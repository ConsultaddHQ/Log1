import os
import json
from operator import or_
from functools import reduce
from django.db.models import Q
from django.utils import timezone
from datetime import date, datetime, timedelta
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from constance import config
from activity.models import Activity
# from utils_app.mailing import send_email
from utils_app.utils import get_timezone, get_slack_tag
from utils_app.thred_mail import send_email as send_email_
from employee.models import tag_users, User
from attachment.serializers import Attachment
from activity.serializers import ActivitySerializer
from utils_app.aws_utils import download_s3_object_beats
from utils_app.slack_notification import MessageCard as slack
from log1.utils import html_to_text, password_generator, write_exception, write_info
from notification.utils import create_notification, push_notification
from consultant.models import Consultant, ConsultantProfile, ConsultantPOC, ConsultantMarketing, EXIT_TYPE_CHOICE, \
    ConsultantRateRevision, Education, Experience, WorkAuth


def create_activity(object_id, model, user, desc, activity_type):
    try:
        content_type = ContentType.objects.get(model=model)
        activity = Activity.objects.create(
            user=user, desc=desc, object_id=object_id,
            content_type=content_type, activity_type=activity_type,
        )
        serializer = ActivitySerializer(activity)
        return serializer.data
    except Exception as error:
        write_exception(message=error)
        return None


def is_caps_consultant(consultant):
    user = consultant.internal_user_profile
    return bool(
        user and user.team and user.team.name and user.team.name.lower() == 'caps'
    )


def is_caps_user(user):
    return bool(user and user.team and user.team.name and user.team.name.lower() == 'caps')


def assign_caps_sick_leave(consultant):
    from project.models import ConsultantLeave
    from utils_app.models import Choice

    content_type = ContentType.objects.get(model='consultantleave')
    sick_leave, _ = Choice.objects.get_or_create(
        content_type=content_type,
        field='leave',
        name='sick_leave',
        defaults={'display_name': 'Sick Leave'}
    )
    return ConsultantLeave.objects.get_or_create(
        consultant=consultant,
        leave_type=sick_leave,
        year=date.today().year,
        is_expired=False,
        defaults={'granted': 48.0, 'balance': 48.0}
    )


def ensure_caps_consultant_for_user(user, request=None):
    if not is_caps_user(user):
        return None, False, False

    consultant = Consultant.objects.filter(internal_user_profile=user).first()
    created = False
    linked_existing = False
    if not consultant:
        consultant = Consultant.objects.filter(email__iexact=user.email).first()
        if consultant and consultant.internal_user_profile_id not in [None, user.id]:
            raise ValueError("A consultant with this CAPS user's email is already linked to another user.")
        if consultant:
            consultant.internal_user_profile = user
            consultant.internal_employee = True
            consultant.name = consultant.name or user.employee_name
            consultant.phone_no = consultant.phone_no or user.phone
            consultant.gender = consultant.gender or user.gender
            consultant.save()
            linked_existing = True
        else:
            consultant = Consultant.objects.create(
                name=user.employee_name,
                email=user.email,
                phone_no=user.phone,
                gender=user.gender,
                internal_employee=True,
                internal_user_profile=user,
                status='on_bench',
                work_type='full_time',
            )
            created = True

    assign_caps_sick_leave(consultant)
    mail_sent = False
    if created or linked_existing:
        mail_sent, _ = send_caps_timetrack_access_mail(consultant, request)
    return consultant, created, mail_sent


def send_caps_timetrack_access_mail(consultant, request=None):
    try:
        if not is_caps_consultant(consultant):
            return False, "not_caps"

        password = password_generator(password_length=10, strength=3)
        consultant.set_password(password)
        consultant.is_active = True
        consultant.first_login = True
        consultant.save()

        mail_data = {
            'template': '../templates/caps_timetrack_access.html',
            'subject': 'Your Consultadd TimeTrack mobile app access',
            'to': [consultant.email],
            'cc': [],
            'bcc': [config.TIMESHEET_APP_ADMIN],
            'context': {
                'iphone_link': config.IPHONE_APP_LINK,
                'android_link': config.ANDROID_APP_LINK,
                'password': password,
                'new_user': True,
                'consultant_name': consultant.name,
                'consultant_email': consultant.email,
            },
        }
        msg, resp, _ = send_email_(mail_data, config.RELATIONS, request)
        if not resp:
            write_exception(msg, request)
            return False, "error"
        return True, "ok"
    except Exception as error:
        write_exception(error, request)
        return False, "error"


def beats_to_log1(file_path, file_name, obj_id, model):
    try:
        content_type = ContentType.objects.get(model=model)
        creator = User.objects.get(employee_id=1000)
        response, error = download_s3_object_beats(file_path, file_name)
        if error:
            write_info(message=str(error), function='beats_to_log1')
            return False, response
        if not os.path.exists(response):
            write_info(message="File not found", function='beats_to_log1')
            return False, "File not found"
        local_file = open(response, 'rb')
        file = ContentFile(local_file.read())
        attachment = Attachment.objects.create(
            creator=creator, attachment_type='other',
            object_id=obj_id, content_type_id=content_type.id,
        )
        attachment.attachment_file.save(response, file, save=True)
        attachment.save()
        os.remove(response)
        return True, response
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
        if terminate.last_date:
            termination_date = datetime.strptime(str(terminate.last_date), '%Y-%m-%d').strftime('%m/%d/%Y')
        else:
            termination_date = "NA"
        payload = {
            "reason": reason,
            "exit_details": exit_details,
            "termination_date": termination_date,
            "consultant": terminate.consultant.name
        }
        # MessageCard.exit_interview_card(payload, request)

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
            "title": title, "body": title,
            "click_action": "https://app.log1.com",
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
        write_exception(message=error, request=request)
        return error


def terminate_consultant(terminate, request):
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
            res, error = send_exit_process_mail(terminate, 'complete', request)
            if error == 'error':
                write_info(message=error, function='terminate_consultant')

        # App Notification
        recruiter = consultant.recruiter
        user_list = [recruiter]
        if recruiter and recruiter.team:
            scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'], is_active=True)
            for user in scrum_masters:
                user_list.append(user)

        if isinstance(terminate.last_date, str):
            last_date = datetime.strptime(terminate.last_date, "%Y-%m-%d").strftime("%b %d, %Y")
        else:
            last_date = terminate.last_date.strftime("%b %d, %Y")

        title = f"{consultant.name} got terminated on {last_date}"
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
            "category": "alert",
            "show_in_foreground": True,
            "title": title, "body": title,
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


def send_exit_process_mail(terminate, exit_status, request):
    try:
        consultant = terminate.consultant
        recruiter = consultant.recruiter
        if consultant.relation:
            poc = consultant.relation
        else:
            poc = consultant.recruiter

        if os.environ.get('ENV', 'local') == 'prod':
            to = [config.RELATIONS, config.FINANCE, config.RECRUITMENT, config.LEGAL]
            cc = [poc.email, config.SUPERADMIN, terminate.created_by.email]


        scrum_masters = User.objects.filter(team=recruiter.team, role__name__in=['admin', 'proxy'], is_active=True)
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
            'to': to, 'cc': cc, 'bcc': [], 'subject': subject,
            'template': '../templates/exit_process.html',
            'context': {
                'rehire': 'Yes' if terminate.rehire else 'No',
                'legal': 'Yes' if terminate.legal_action else 'No',
                'resign_date': resign_date, 'exit_status': exit_status,
                'title': title, 'reason': reason, 'last_date': last_date,
                'type': types[terminate.type], 'consultant': consultant.name,
                'exit_details': exit_details if terminate.exit_details else 'NA',
                'consultant_email': consultant.email, 'recruiter': recruiter.employee_name,
                'notice_period': terminate.notice_period if terminate.legal_action else 'NA',
                'cancel_reason': terminate.cancel_reason if terminate.cancel_reason else 'NA',
            },
        }
        res, msg, from_id = send_email_(mail_data, terminate.created_by.email, request=request)
        if not msg:
            return res, "error"
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
            if marketing.primary_marketer:
                user_list.append(marketing.primary_marketer)
        notification_data = {
            'category': 'info', 'sender_id': sender.id,
            'description': title, 'recipient_user_type': 'user',
            'target_type': sub_target, 'sender_user_type': 'user',
            'parent_id': consultant.id, 'parent_type': 'consultant',
            'title': title, 'target_id': target_id if target_id else consultant.id,
        }
        create_notification(user_list, notification_data)

        # Push Notification
        message_body = {
            "title": title, "body": title,
            "click_action": "https://app.log1.com",
            "category": "info", "show_in_foreground": True,
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


def fetch_consultant_count(team):
    day_one = datetime.today().replace(day=1, hour=0, minute=0)
    team_count = "NA"
    if team:
        team_count = Consultant.objects.filter(created__date__gte=day_one, pocs__poc__team=team).count()
    total_count = Consultant.objects.filter(created__date__gte=day_one).count()
    return total_count, team_count


def new_recruit_notification(consultant, request):
    try:
        cfr = request.data.get('cfr', "NA")
        source = request.data.get('source', "NA")
        feedback = request.data.get('feedback', "NA")
        visa, rate, recruiter_name, recruiter_team = "NA", "NA", "NA", None
        recruiter_gender = ':man::skin-tone-2:'
        qs = ConsultantPOC.objects.filter(consultant=consultant, poc_type='recruiter')
        if qs:
            recruiter = qs.first().poc
            recruiter_team = recruiter.team
            recruiter_name = get_slack_tag(recruiter)
            if recruiter.gender == 'female':
                recruiter_gender = ':red_haired_woman::skin-tone-2:'

        total_count, team_count = fetch_consultant_count(recruiter_team)
        qs = WorkAuth.objects.filter(consultant=consultant)
        if qs:
            visa = qs.first().get_visa_type_display()
        qs = ConsultantRateRevision.objects.filter(consultant=consultant)
        if qs:
            rate = qs.first().rate

        consultant_gender = ':red_haired_woman::skin-tone-2:' if consultant.gender == 'female' else ':man::skin-tone-2:'
        payload = {
            "cfr": cfr,
            "visa": visa,
            "rate": rate,
            "source": source,
            "feedback": feedback,
            "team_count": team_count,
            "total_count": total_count,
            "gender": consultant_gender,
            "recruiter_name": recruiter_name,
            "recruiter_team": recruiter_team,
            "recruiter_gender": recruiter_gender,
        }
        slack.new_recruit_card(consultant, payload, request)
    except Exception as error:
        write_exception(message=error, request=request)


def add_other_details(request, consultant):
    try:
        consultant_id = consultant.id
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

        if not consultant.attachments.all().exists():
            for document in documents:
                res, res_data = beats_to_log1(
                    model='consultant',
                    obj_id=consultant_id,
                    file_path=document['file_path'],
                    file_name=document['file_name'],
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
        req_phone_number = request.data.get('primary_no', [])

        if req_skills and None not in req_skills:
            skills = ", ".join(req_skills)
        if req_links and None not in req_links:
            links = ", ".join(req_links)

        qs = Consultant.objects.filter(email=request.data.get('email'))
        if qs:
            consultant = qs.first()
            result, msg = add_other_details(request, consultant)
            if msg == 'error':
                write_info(result, 'create_consultant', request)
            return consultant, "exists"
        else:
            current_city = request.data.get('current_location', None)
            if current_city:
                location = current_city.split(",")
                if len(location) > 1:
                    current_city = f'{location[0].replace(" ", "")},{location[1].replace(" ", "")}'

            consultant = Consultant.objects.create(
                is_active=True,
                work_type='full_time',
                phone_no=req_phone_number,
                current_city=current_city,
                links=links, skills=skills,
                ssn=request.data.get('ssn'),
                name=request.data.get('name'),
                email=request.data.get('email'),
                skype=request.data.get('skype_id'),
                gender=request.data.get('gender'),
                country=request.data.get('country'),
                date_of_birth=request.data.get('dob'),
                marital_status=request.data.get('marital_status', 'unmarried'),
                internal_employee=request.data.get('internal_employee', False),
            )
            consultant_id = consultant.id
            if consultant.current_city:
                consultant.timezone = get_timezone(consultant.current_city)
                consultant.save()

            # Adding Recruiter of Consultant
            recruiter_employee_email = request.data.get('recruiter')
            recruiter_employee_id = request.data.get('recruiter_emp_id')
            qs = User.objects.filter(email=recruiter_employee_email)
            if qs:
                recruiter = qs.first()
                ConsultantPOC.objects.create(
                    poc=recruiter,
                    start=timezone.now(),
                    poc_type='recruiter',
                    consultant_id=consultant_id,
                )
            else:
                try:
                    recruiter = get_object_or_404(User, employee_id=recruiter_employee_id)
                    ConsultantPOC.objects.create(
                        poc=recruiter,
                        start=timezone.now(),
                        poc_type='recruiter',
                        consultant_id=consultant_id,
                    )
                except User.DoesNotExist:
                    pass

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
            visa_details = json.loads(request.data.get('work_auth', '[]'))[0] \
                if request.data.get('work_auth', None) else []
            education = json.loads(request.data.get('education', '[]'))[0] \
                if request.data.get('education', None) else []
            ConsultantProfile.objects.create(
                title="Original",
                consultant_id=consultant_id,
                profile_owner_id=creator_id,
                links=links,
                date_of_birth=request.data.get('dob'),
                visa_end=visa_details['end'],
                visa_type=visa_details['type']['name'],
                visa_start=visa_details['start'],
                current_city=request.data.get('current_location'),
                education=education['edu_type']['name']
            )

            add_other_details(request, consultant)
            new_recruit_notification(consultant, request)
            return consultant, "ok"
    except Exception as error:
        write_exception(error, request)
        return error, "error"


def marketing_days_filter(days):
    day_filter = dict()
    day_filter["marketing__status"] = 'open'
    if days == 'lt_12':
        day_filter['marketing__start__gt'] = timezone.now().date() - timedelta(days=12)
    elif days == 'lt_24':
        day_filter['marketing__start__gt'] = timezone.now().date() - timedelta(days=24)
    elif days == 'lt_36':
        day_filter['marketing__start__gt'] = timezone.now().date() - timedelta(days=36)
    elif days == 'gt_36':
        day_filter['marketing__start__lte'] = timezone.now().date() - timedelta(days=36)
    return day_filter


def queryset_filter_by_status(queryset, sub_status, offer_candidates=None):
    if sub_status == 'non_pool':
        queryset = queryset.filter(marketing__in_pool=False, marketing__status='open')

    elif sub_status == 'in_pool':
        queryset = queryset.filter(
            marketing__in_pool=True, marketing__status='open'
        ).exclude(id__in=offer_candidates)

    elif sub_status == 'on_boarded':
        queryset = queryset.filter(
            projects__statuses__status='on_boarded',
            projects__statuses__is_current=True
        )

    elif sub_status == 'in_offer':
        queryset = queryset.filter(
            projects__statuses__status__in=['new', 'received'],
            projects__statuses__is_current=True
        )

    elif sub_status == 'fired':
        queryset = queryset.filter(exit__type='fired')

    elif sub_status == 'resigned':
        queryset = queryset.filter(exit__type='resigned')

    elif sub_status == 'absconded':
        queryset = queryset.filter(exit__type='absconded')

    return queryset


def status_filter_obj(consultants, open_candidates, offer_candidates):
    consultants = consultants.distinct()
    return {
        "all": consultants,
        "terminated": consultants.filter(status='terminated'),

        "marketing_candidate": consultants.filter(
            status='on_bench', marketing__status='close'
        ).exclude(id__in=open_candidates),

        "on_project": consultants.filter(
            projects__statuses__status='joined', projects__statuses__is_current=True
        ).exclude(status='terminated'),

        "offer": consultants.filter(
            projects__statuses__is_current=True,
            projects__statuses__status__in=['new', 'received', 'on_boarded'],
        ).exclude(status='terminated'),

        "on_bench": consultants.filter(marketing__status='open').exclude(id__in=offer_candidates)
    }


def sub_status_filter_obj(consultants, con_status, offer_candidates):
    sub_status_obj = dict()
    if con_status == 'on_bench':
        sub_status_obj = {
            'in_pool': queryset_filter_by_status(consultants, 'in_pool', offer_candidates).count(),
            'non_pool': queryset_filter_by_status(consultants, 'non_pool', offer_candidates).count(),
        }

    elif con_status == 'offer':
        sub_status_obj = {
            'in_offer': queryset_filter_by_status(consultants, 'in_offer').count(),
            'on_boarded': queryset_filter_by_status(consultants, 'on_boarded').count(),
        }

    elif con_status == 'terminated':
        sub_status_obj = {
            'fired': queryset_filter_by_status(consultants, 'fired').count(),
            'resigned': queryset_filter_by_status(consultants, 'resigned').count(),
            'absconded': queryset_filter_by_status(consultants, 'absconded').count(),
        }
    return sub_status_obj


def candidate_filter(request):
    try:
        query = request.GET.get('query', None)
        con_status = request.GET.get('status', '')
        filter_json = request.GET.get('filter_json', None)
        con_sub_status = request.GET.get('sub_status', None)
        consultants = Consultant.objects.all()

        if filter_json:
            filters = json.loads(filter_json)

            if 'gender' in filters:
                consultants = consultants.filter(gender=filters['gender'])

            if 'city' in filters:
                consultants = consultants.filter(current_city__in=filters.get('city'))

            if 'preferred_location' in filters:
                consultants = consultants.filter(marketing__preferred_location__in=filters.get('preferred_location'))

            if 'days_on_bench' in filters:
                day_filter = marketing_days_filter(filters['days_on_bench'])
                consultants = consultants.filter(**day_filter)

            if 'recruiter' in filters:
                consultants = consultants.filter(
                    pocs__poc_id=filters['recruiter'], pocs__poc_type='recruiter', pocs__end=None
                )

            if 'retention' in filters:
                consultants = consultants.filter(
                    pocs__poc_id=filters['retention'], pocs__poc_type='retention', pocs__end=None
                )

            if 'team' in filters and len(filters['team']) > 0:
                consultants = consultants.filter(
                    marketing__teams__name__iexact=filters['team'], marketing__status='open'
                )

            if 'visa' in filters:
                consultants = consultants.filter(
                    work_auth__visa_type=filters['visa'], work_auth__is_current=True
                )

            if 'jobPosition' in filters:
                consultants = consultants.filter(
                    marketing__submissions__project__statuses__status='joined',
                    marketing__submissions__lead__position__id__in=filters['jobPosition'],
                    marketing__submissions__project__statuses__is_current=True, status='on_project'
                )

            if 'visa_end' in filters:
                consultants = consultants.filter(
                    work_auth__visa_end__lte=filters['visa_end'], work_auth__is_current=True
                )

            if 'rtg' in filters:
                consultants = consultants.filter(marketing__rtg=filters['rtg'], marketing__status='open')

            if 'skill' in filters and len(filters["skill"]) > 0:
                consultants = consultants.filter(reduce(or_, [Q(skills__icontains=q) for q in filters['skill']]))

            if 'dob' in filters:
                if 'lte' in filters['dob'] and filters['dob'].get('lte'):
                    lte = (datetime.strptime(
                        filters['dob']['lte'], '%Y-%m-%d').date() + timedelta(days=1)).strftime("%Y-%m-%d")
                    consultants = consultants.filter(date_of_birth__lte=lte)
                if 'gte' in filters['dob']:
                    consultants = consultants.filter(
                        date_of_birth__gte=filters['dob'].get('gte', None)
                    )

            if 'created' in filters:
                if 'lte' in filters['created'] and filters['created'].get('lte'):
                    lte = (datetime.strptime(
                        filters['created']['lte'], '%Y-%m-%d').date() + timedelta(days=1)).strftime("%Y-%m-%d")
                    consultants = consultants.filter(created__lte=lte)
                if 'gte' in filters['created']:
                    consultants = consultants.filter(
                        created__gte=filters['created'].get('gte', None)
                    )

        if query:
            query = query.lstrip().replace(':amp:', '&')
            consultants = consultants.filter(
                Q(name__icontains=query) |
                Q(email__iexact=query)
            )

        consultants = Consultant.objects.filter(
            id__in=consultants.distinct('id').order_by('id').values_list('id', flat=True)
        )

        open_candidates = consultants.filter(marketing__status='open').values('id')
        offer_candidates = consultants.filter(
            projects__statuses__status__in=['new', 'received', 'on_boarded'], projects__statuses__is_current=True
        ).values('id')

        status_obj = status_filter_obj(consultants, open_candidates, offer_candidates)

        if con_status and len(con_status) > 0:
            consultants = status_obj[con_status]

        sub_status_obj = sub_status_filter_obj(consultants, con_status, offer_candidates)

        consultants = queryset_filter_by_status(consultants, con_sub_status, offer_candidates)

        return consultants, {"status_obj": status_obj, "sub_status_obj": sub_status_obj}
    except Exception as error:
        write_exception(error, request)
        return str(error), "error"


def create_and_send_notification(consultant, feedback, title, user_list, request):
    try:
        notification_data = {
            'title': title,
            'category': 'info',
            'description': title,
            'target_id': feedback.id,
            'sender_user_type': 'user',
            'parent_id': consultant.id,
            'parent_type': 'consultant',
            'sender_id': request.user.id,
            'recipient_user_type': 'user',
            'target_type': 'consultantfeedback',
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
                'target_id': consultant.id,
                'sub_target_id': feedback.id,
                'timestamp': str(datetime.now()),
                'sub_target': 'consultantfeedback',
            },
        }
        object_ids = [user.id for user in user_list]
        push_notification(object_ids, message_body)
        return False
    except Exception as error:
        write_exception(message=error, request=request)
        return str(error)
