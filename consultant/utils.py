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
from utils_app.utils import get_timezone
from utils_app.mailing import send_email
from employee.models import tag_users, User
from attachment.serializers import Attachment
from activity.serializers import ActivitySerializer
from utils_app.slack_notification import MessageCard as slack
from utils_app.teams_notification import MessageCard as teams
from utils_app.aws_utils import download_s3_object_beats
from utils_app.slack_notification import MessageCard as slack
from log1.utils import html_to_text, write_exception, write_info
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
        else:
            cc, bcc = [], []
            to = ['suman.buie.cpp@gmail.com', 'shreyaskhede26@gmail.com', 'log1.consultadd@gmail.com']

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
        res, msg = send_email(mail_data, terminate.created_by.email, request=request)
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
        visa, rate, recruiter, recruiter_team = "NA", "NA", "NA", None
        recruiter_gender = ':man::skin-tone-2:'
        qs = ConsultantPOC.objects.filter(consultant=consultant, poc_type='recruiter')
        if qs:
            recruiter = qs.first().poc
            recruiter_team = recruiter.team
            recruiter_name = recruiter.name
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
            "recruiter_team": recruiter_team,
            "recruiter_gender": recruiter_gender,
        }
        slack.new_recruit_card(consultant, payload, request)
        teams.new_recruit_card(consultant, payload, request)
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
            result, msg = add_other_details(request, consultant)
            if msg == 'error':
                write_info(result, 'create_consultant', request)
            return consultant, "exists"
        else:
            consultant = Consultant.objects.create(
                work_type='full_time',
                phone_no=phone_numbers,
                links=links, skills=skills,
                ssn=request.data.get('ssn'),
                name=request.data.get('name'),
                email=request.data.get('email'),
                skype=request.data.get('skype'),
                gender=request.data.get('gender'),
                date_of_birth=request.data.get('dob'),
                current_city=request.data.get('current_location'),
                marital_status=request.data.get('marital_status', 'unmarried'),
                internal_employee=request.data.get('internal_employee', False),
            )
            consultant_id = consultant.id
            if consultant.current_city:
                consultant.timezone = get_timezone(consultant.current_city)
                consultant.save()

            # Adding Recruiter of Consultant
            recruiter_employee_email = request.data.get('recruiter')
            qs = User.objects.filter(email=recruiter_employee_email)
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

            if 'visa_end' in filters:
                consultants = consultants.filter(
                    work_auth__visa_end__lte=filters['visa_end'], work_auth__is_current=True
                )

            if 'rtg' in filters:
                consultants = consultants.filter(marketing__rtg=filters['rtg'], marketing__status='open')

            if 'skill' in filters and len(filters["skill"]) > 0:
                consultants = consultants.filter(reduce(or_, [Q(skills__icontains=q) for q in filters['skill']]))

            if 'dob' in filters:
                if 'lte' in filters['dob']:
                    consultants = consultants.filter(
                        date_of_birth__year__lte=filters['dob']['lte']
                    )
                elif 'gte' in filters['dob']:
                    consultants = consultants.filter(
                        date_of_birth__year__gte=filters['dob']['gte']
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
