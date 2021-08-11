import json
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from employee.models import User
from log1.utils import write_exception
from consultant.models import ConsultantProfile
from attachment.models import create_attachment
from marketing.models import Submission, Interview


def vendor_account_manager(vendor_company):
    file = open('fixtures/am_config.json', 'r')
    data = json.loads(file.read())
    vendor_company = vendor_company.replace(" ", "").replace(",", "").replace("-", "").replace("_", "").lower()
    for email, vendors in data.items():
        if vendor_company in vendors:
            return email
    return None


def get_scrum_masters(request):
    return User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])


def get_users_and_attendees(request, interview):
    user_list = [interview.supervisor]
    attendees = [{'email': interview.supervisor.email}, {'email': request.user.email}]
    scrum_masters = User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])

    for user in interview.guest.all().union(scrum_masters):
        user_list.append(user)
        attendees.append({"email": user.email})

    email = vendor_account_manager(interview.submission.lead.vendor_company.name)
    if email:
        attendees.append({"email": email})

    return user_list, attendees


def date_filter(queryset, created, field_str):
    filters = dict()
    if created and type(created) == dict:
        lte = created.get('lte', None)
        gte = created.get('gte', None)
        if lte:
            filters[f"{field_str}__lte"] = lte
        if gte:
            filters[f"{field_str}__gte"] = gte
    return queryset.filter(**filters)


# Change status of scheduled and rescheduled Interviews to feedback_due
def change_to_feedback_due():
    try:
        now = datetime.now() - timedelta(hours=4)
        previous_interviews = Interview.objects.filter(end_time__lte=now, status__in=['scheduled', 'rescheduled'])
        for interview in previous_interviews:
            interview.status = 'feedback_due'
            interview.save()
    except Exception as error:
        write_exception(message=error)
        return None


def submission_is_complete(obj):
    try:
        if obj.rate and obj.vendor and obj.client and (obj.lead.job_desc and len(obj.lead.job_desc) > 20):
            obj.is_complete = True
            obj.save()
            return True
        return False
    except Exception as error:
        write_exception(message=error)
        return False


def get_interview_title(interview):
    try:
        return f"""CTB: {interview.supervisor.employee_name} :: {interview.round}R :: 
            {interview.get_screening_type_display()} :: {interview.get_interview_mode_display()} :: 
            {interview.start_time.strftime('%m/%d/%Y :: %I:%M %p EST')} :: {interview.submission.client} :: 
            {interview.consultant.name} :: {interview.marketer.employee_name}"""
    except Exception as error:
        write_exception(message=error)
        return False


def create_submission(request, lead_id):
    try:
        profile = get_object_or_404(ConsultantProfile, id=request.data['profile_id'])
        vendor_contact = request.data.get('vendor_contact', None)
        sub, created = Submission.objects.get_or_create(
            status='sub',
            lead_id=lead_id,
            created_by=request.user,
            rate=request.data['rate'],
            email=request.data['email'],
            phone=request.data['phone'],
            client=request.data['client'],
            employer=request.data['employer'],
            consultant_marketing_id=request.data['marketing_id'],

            other_link=profile.links,
            visa_end=profile.visa_end,
            linkedin=profile.linkedin,
            education=profile.education,
            visa_type=profile.visa_type,
            visa_start=profile.visa_start,
            current_city=profile.current_city,
            date_of_birth=profile.date_of_birth,
        )
        if vendor_contact:
            sub.vendor_contact_id = request.data['vendor_contact']
            sub.save()

        submission_is_complete(sub)

        resume = request.FILES.get('file_resume', None)
        if resume:
            resume_data = {
                "file": resume,
                "type": 'resume',
                "object_id": sub.id,
                "model": "submission",
                "creator": request.user,
            }
            create_attachment(resume_data)

        other = request.FILES.get('file_other', None)
        if other:
            other_file_data = {
                "file": other,
                "type": 'other',
                "object_id": sub.id,
                "model": "submission",
                "creator": request.user,
            }
            create_attachment(other_file_data)

        return sub, "ok"
    except Exception as error:
        write_exception(error, request)
        return error, "error"
