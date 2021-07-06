import os
import json
import boto3
from django.utils import timezone
from datetime import date, datetime, timedelta
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from constance import config
from activity.models import Activity
from utils_app.mailing import send_email
from employee.models import tag_users, User
from attachment.serializers import Attachment
from activity.serializers import ActivitySerializer
from notification.utils import create_notification, push_notification
from log1.utils import post_msg_using_webhook, html_to_text, write_exception, write_info
from consultant.models import Consultant, ConsultantProfile, ConsultantPOC, ConsultantMarketing, EXIT_TYPE_CHOICE, \
    ConsultantRateRevision, Education, Experience, WorkAuth


def create_activity(object_id, model, user, desc, activity_type):
    content_type = ContentType.objects.get(model=model)
    activity = Activity.objects.create(
        user=user,
        desc=desc,
        object_id=object_id,
        content_type=content_type,
        activity_type=activity_type,
    )
    serializer = ActivitySerializer(activity)
    return serializer.data


def download_s3_object_beats(key, name):
    try:
        local_path = f'media/beats/{name}'
        s3 = boto3.client(
            's3', region_name=os.getenv('AWS_REGION_NAME'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        s3.download_file(os.getenv('AWS_BEATS_BUCKET'), key, local_path)
        return True, local_path
    except Exception as error:
        write_exception(message=error)
        return False, error


def beats_to_log1(file_path, file_name, obj_id, model):
    try:
        content_type = ContentType.objects.get(model=model)
        creator = User.objects.get(employee_id=1000)
        msg, path = download_s3_object_beats(file_path, file_name)
        if not msg:
            return False, path
        if not os.path.exists(path):
            return False, "File not found"
        local_file = open(path, 'rb')
        file = ContentFile(local_file.read())
        attachment = Attachment.objects.create(
            creator=creator,
            object_id=obj_id,
            attachment_type='other',
            content_type_id=content_type.id,
        )
        attachment.attachment_file.save(path, file, save=True)
        attachment.save()
        os.remove(path)
        return True, path
    except Exception as error:
        write_exception(message=error)
        return False, error


def close_marketing():
    try:
        queryset = ConsultantMarketing.objects.filter(end__lte=date.today(), status='open')
        queryset.update(status='close')
        admin = get_object_or_404(User, employee_id=1000)

        # Push Notification
        for marketing in queryset:
            title = f"{marketing.consultant.name}'s marketing cycle stopped by {admin.employee_name}"
            send_notification_for_user(marketing.consultant, admin, title, 'marketing')
        return None
    except Exception as error:
        write_exception(message=error)
        return error


def start_marketing():
    try:
        consultants = Consultant.objects.filter(status__in=['on_bench', 'on_project'], marketing__status='open')
        queryset = ConsultantMarketing.objects.filter(
            start__lte=date.today(), status='close', end=None
        ).exclude(consultant_id__in=consultants.values('id'))
        queryset.update(status='open')
        admin = get_object_or_404(User, employee_id=1000)

        # Push Notification
        for marketing in queryset:
            title = f"{marketing.consultant.name}'s new marketing cycle started by {admin.employee_name}"
            send_notification_for_user(marketing.consultant, admin, title, 'marketing')
        return None
    except Exception as error:
        write_exception(message=error)
        return error


def send_exit_interview_detail(terminate, request):
    try:
        # Message for Exit Interview
        exit_details = html_to_text(terminate.exit_details)
        reason = ", ".join(reason.name for reason in terminate.reasons.all())
        termination_date = datetime.strptime(str(terminate.last_date), '%Y-%m-%d').strftime('%m/%d/%Y')
        data = {
            "title": f"Exit interview for {terminate.consultant.name}",
            "text": f"**Reason for leaving** : {reason}<br>"
                    f"**Termination Date** : {termination_date}<br>"
                    f"**Exit Interview Details** : {exit_details} <br>"
        }
        post_msg_using_webhook(config.exit_interview_url, data)
        user_list = []
        tags = request.data.get('tagged_user', [])
        if len(tags) > 0:
            for tag in tags:
                user = get_object_or_404(User, id=tag)
                user_list.append(user)
            tag_data = {
                "model": "consultantexit",
                "object_id": terminate.id,
                "tags": tags
            }
            tag_users(tag_data)
        title = f"{request.user.employee_name} tagged you in a exit interview of {terminate.consultant.name}"
        notification_data = {
            'title': title,
            'category': 'info',
            'description': title,
            'target_id': terminate.id,
            'sender_user_type': 'user',
            'parent_type': 'consultant',
            'sender_id': request.user.id,
            'recipient_user_type': 'user',
            'target_type': 'consultantexit',
            'parent_id': terminate.consultant.id,
        }
        create_notification(user_list, notification_data)

        # Push Notification
        message_body = {
            "category": "alert",
            "show_in_foreground": True,
            "click_action": "https://app.log1.com",
            "body": title,
            "title": title,
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target': 'consultant',
                'sub_target': 'terminate',
                'sub_target_id': terminate.id,
                'timestamp': str(datetime.now()),
                'target_id': terminate.consultant.id,
            },
        }
        object_ids = [user.id for user in user_list]
        push_notification(object_ids, message_body)

        return None
    except Exception as error:
        write_exception(message=error)
        return error


def terminate_consultant(terminate):
    try:
        consultant = terminate.consultant
        consultant.status = 'terminated'
        consultant.save()

        queryset = consultant.marketing.filter(status='open')
        for marketing in queryset:
            marketing.status = 'close'
            marketing.end = date.today()
            marketing.save()

        terminate.status = 'complete'
        terminate.save()

        # Email for Exit Process Cancelled
        if os.environ.get('ENV', 'local') == 'prod':
            res, error = send_exit_process_mail(terminate, 'complete')
            if error == 'error':
                write_info(message=error, function='terminate_consultant')

        # App Notification
        recruiter = consultant.recruiter
        user_list = [recruiter]
        scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
        for user in scrum_masters:
            user_list.append(user)

        last_date = datetime.strptime(terminate.last_date, "%Y-%m-%d").strftime("%b. %d, %Y")
        title = f"""{consultant.name} got terminated on {last_date}"""

        notification_data = {
            'title': title,
            'category': 'info',
            'target_id': terminate.id,
            'sender_user_type': 'user',
            'parent_type': 'consultant',
            'recipient_user_type': 'user',
            'description': terminate.type,
            'target_type': 'consultantexit',
            'sender_id': terminate.created_by.id,
            'parent_id': terminate.consultant.id,
        }
        create_notification(user_list, notification_data)

        # Push Notification
        message_body = {
            "body": title,
            "title": title,
            "category": "alert",
            "show_in_foreground": True,
            "click_action": "https://app.log1.com",
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target': 'consultant',
                'sub_target': 'terminate',
                'sub_target_id': terminate.id,
                'target_id': terminate.consultant.id,
                'timestamp': str(timezone.now().strftime('%m/%d/%Y')),
            },
        }

        object_ids = []
        for user in user_list:
            object_ids.append(user.id)
        push_notification(object_ids, message_body)
        return None
    except Exception as error:
        write_exception(message=error)
        return error


def send_exit_process_mail(terminate, exit_status):
    try:
        consultant = terminate.consultant
        recruiter = consultant.recruiter
        if consultant.relation:
            poc = consultant.relation
        else:
            poc = consultant.recruiter

        to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL]
        cc = [poc.email, config.SUPERADMIN, terminate.created_by.email]

        scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'])
        for user in scrum_masters:
            cc.append(user.email)

        queryset = consultant.marketing.filter(status='open')
        for marketing in queryset:
            cc.append(marketing.primary_marketer.email)

        types = dict(EXIT_TYPE_CHOICE)

        if terminate.reasons.all():
            reason = ", ".join(reason.name for reason in terminate.reasons.all())
        else:
            reason = 'NA'

        subject = f'Exit Process Initiated for {consultant.name}'
        title = "Exit Process Initiated"

        if exit_status == 'cancel':
            subject = f'Exit Process Cancelled for {consultant.name}'
            title = "Exit Process Cancelled"

        elif exit_status == 'complete':
            subject = f'{consultant.name} Terminated'
            title = "Exit Process Complete, Employee Terminated"

        exit_details = html_to_text(terminate.exit_details)

        last_date = 'NA'
        if terminate.last_date:
            last_date = datetime.strptime(terminate.last_date, "%Y-%m-%d").strftime("%b. %d, %Y")

        resign_date = 'NA'
        if terminate.resign_date:
            resign_date = datetime.strptime(terminate.resign_date, "%Y-%m-%d").strftime("%b. %d, %Y")

        mail_data = {
            'to': to,
            'cc': cc,
            'bcc': [],
            'subject': subject,
            'template': '../templates/exit_process.html',
            'context': {
                'title': title,
                'reason': reason,
                'last_date': last_date,
                'resign_date': resign_date,
                'exit_status': exit_status,
                'type': types[terminate.type],
                'consultant': consultant.name,
                'consultant_email': consultant.email,
                'recruiter': recruiter.employee_name,
                'rehire': 'Yes' if terminate.rehire else 'No',
                'legal': 'Yes' if terminate.legal_action else 'No',
                'exit_details': exit_details if terminate.exit_details else 'NA',
                'cancel_reason': terminate.cancel_reason if terminate.cancel_reason else 'NA',
                'notice_period': terminate.notice_period if terminate.legal_action else 'NA',
            },
        }
        res = send_email(mail_data, terminate.created_by.email)
        return res, "ok"
    except Exception as error:
        write_exception(message=error)
        return error, "error"


def send_notification_for_user(consultant, sender, title, sub_target, target_id=None):
    try:
        # App Notification
        user_list = []
        pocs = consultant.pocs.all()
        for user in pocs:
            user_list.append(user.poc)
        marketing = consultant.marketing.filter(status='open').first()
        if marketing:
            marketers = marketing.marketer.all()
            for marketer in marketers:
                user_list.append(marketer)
            user_list.append(marketing.primary_marketer)
        notification_data = {
            'title': title,
            'category': 'info',
            'description': title,
            'sender_id': sender.id,
            'target_type': sub_target,
            'sender_user_type': 'user',
            'parent_id': consultant.id,
            'parent_type': 'consultant',
            'recipient_user_type': 'user',
            'target_id': target_id if target_id else consultant.id,
        }
        create_notification(user_list, notification_data)

        # Push Notification
        message_body = {
            "body": title,
            "title": title,
            "category": "info",
            "show_in_foreground": True,
            "click_action": "https://app.log1.com",
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target': 'consultant',
                'sub_target': sub_target,
                'target_id': consultant.id,
                'timestamp': str(datetime.now()),
            },
        }
        object_ids = [user.id for user in user_list]
        push_notification(object_ids, message_body)
        return "Notification sent"
    except Exception as error:
        write_exception(message=error)
        return error, "error"


def add_other_details(request, consultant_id):
    try:
        work_auths, experiences, educations, documents = [], [], [], []
        if 'work_auth' in request.data:
            work_auths = json.loads(request.data.get('work_auth'))

        if not WorkAuth.objects.filter(consultant_id=consultant_id).exists():
            for visa in work_auths:
                WorkAuth.objects.create(
                    visa_end=visa['end'],
                    visa_start=visa['start'],
                    is_current=visa['current'],
                    consultant_id=consultant_id,
                    visa_type=visa['type']["name"],
                )

        if 'education' in request.data:
            educations = json.loads(request.data.get('education'))

        if not Education.objects.filter(consultant_id=consultant_id).exists():
            for education in educations:
                Education.objects.create(
                    city=education['city'],
                    major=education['major'],
                    remark=education['remark'],
                    consultant_id=consultant_id,
                    org_name=education['org_name'],
                    end_date=education['end_date'],
                    edu_type=education['edu_type']['name'],
                )

        if 'experience' in request.data:
            experiences = json.loads(request.data.get('experience'))

        if not Experience.objects.filter(consultant_id=consultant_id).exists():
            for experience in experiences:
                Experience.objects.create(
                    city=experience['city'],
                    title=experience['title'],
                    remark=experience['remark'],
                    consultant_id=consultant_id,
                    company=experience['company'],
                    end_date=experience['end_date'],
                    start_date=experience['start_date'],
                    exp_type=experience['exp_type']['name'],
                )

        # Adding Documents
        if 'documents' in request.data:
            documents = json.loads(request.data.get('documents'))

        for document in documents:
            res, res_data = beats_to_log1(
                document['file_path'],
                document['file_name'],
                consultant_id,
                'consultant'
            )
            if not res:
                write_info(res_data, 'add_other_details', request)
                return res_data, "error"
        return "Details added", "ok"
    except Exception as error:
        write_exception(error, request)
        return error, "error"


def create_consultant(request, creator_id):
    try:
        skills, links, phone_numbers = None, None, None
        req_links = request.data.get('links', [])
        req_skills = request.data.get('skills', [])
        req_phone_numbers = request.data.get('phone_numbers', [])
        if req_skills and None not in req_skills:
            skills = ", ".join(req_skills)
        if req_links and None not in req_links:
            links = ", ".join(req_links)
        if req_phone_numbers and None not in req_phone_numbers:
            phone_numbers = ", ".join(req_phone_numbers)

        qs = Consultant.objects.filter(email=request.data.get('email'))
        if qs:
            consultant = qs.first()
            consultant_id = consultant.id
            result, msg = add_other_details(request, consultant_id)
            if msg == 'error':
                write_info(result, 'create_consultant', request)
            return consultant, "exists"
        else:
            consultant = Consultant.objects.create(
                links=links,
                skills=skills,
                work_type='full_time',
                phone_no=phone_numbers,
                ssn=request.data.get('ssn'),
                name=request.data.get('name'),
                email=request.data.get('email'),
                skype=request.data.get('skype'),
                gender=request.data.get('gender'),
                date_of_birth=request.data.get('dob'),
                current_city=request.data.get('current_location')
            )
            consultant_id = consultant.id

            # Adding Recruiter of Consultant
            recruiter_employee_id = request.data.get('recruiter')
            qs = User.objects.filter(email=recruiter_employee_id)
            if qs:
                recruiter = qs.first()
                ConsultantPOC.objects.create(
                    poc=recruiter,
                    start=timezone.now(),
                    poc_type='recruiter',
                    consultant_id=consultant_id,
                )

            # Adding rate
            rate = request.data.get('rate', None)
            if rate:
                ConsultantRateRevision.objects.create(
                    rate=rate,
                    previous_rate=0,
                    start=date.today(),
                    consultant_id=consultant_id
                )

            # Creating Consultant Original Profile Consultant
            ConsultantProfile.objects.create(
                title="Original",
                consultant_id=consultant_id,
                profile_owner_id=creator_id,
                links=request.data.get('links'),
                date_of_birth=request.data.get('dob'),
                visa_end=request.data.get('visa_end'),
                visa_type=request.data.get('visa_type'),
                visa_start=request.data.get('visa_start'),
                current_city=request.data.get('current_location'),
            )

            add_other_details(request, consultant_id)
            return consultant, "ok"
    except Exception as error:
        write_exception(error, request)
        return error, "error"


def marketing_days_filter(days):
    day_filter = dict()
    day_filter["marketing__status"] = 'open'
    if days == 'lt_12':
        day_filter['marketing__start__gte'] = timezone.now().date() - timedelta(days=12)
    elif days == 'lt_24':
        day_filter['marketing__start__gte'] = timezone.now().date() - timedelta(days=24)
    elif days == 'lt_36':
        day_filter['marketing__start__gte'] = timezone.now().date() - timedelta(days=36)
    elif days == 'gt_36':
        day_filter['marketing__start__lte'] = timezone.now().date() - timedelta(days=36)
    return day_filter
