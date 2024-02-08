import os
import csv
import json

from pytz import timezone

from celery import shared_task
from django.http import HttpResponse
from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

from constance import config
from employee.models import User
from utils_app.models import Choice
from consultant.models import ConsultantProfile
from attachment.models import create_attachment
from notification.models import FCMDevice, UserNotification
from marketing.serializers import InterviewerProfileSerializer
from marketing.models import Submission, Interview, Question, Answer, InterviewerProfile, GuestInfo

from log1.utils import write_info, write_exception
from utils_app.slack_notification import MessageCard as slack
from notification.utils import push_notification_consultant, create_notification


def vendor_account_manager(vendor_company):
    try:
        file = open('fixtures/am_config.json', 'r')
        data = json.loads(file.read())
        vendor_company = vendor_company.replace(" ", "").replace(",", "").replace("-", "").replace("_", "").lower()
        for email, vendors in data.items():
            if vendor_company in vendors:
                return email
        return None
    except Exception as error:
        write_exception(message=error)
        return None


def get_scrum_masters(request):
    return User.objects.filter(team=request.user.team, role__name__in=['admin', 'proxy'])


def get_users_and_attendees(request, interview):
    try:
        user_list = [interview.supervisor]
        attendees = [{'email': interview.submission.created_by.email}]
        if interview.supervisor.is_active:
            attendees.append({'email': interview.supervisor.email})
        if 'engineer' not in request.user.roles:
            scrum_masters = User.objects.filter(
                team=request.user.team, role__name__in=['admin', 'proxy'], account_login=True
            )
            for user in scrum_masters:
                user_list.append(user)
                attendees.append({"email": user.email})
        else:
            scrum_masters = User.objects.filter(
                team=interview.submission.marketing_team, role__name__in=['admin', 'proxy'], account_login=True
            )
            for user in scrum_masters:
                user_list.append(user)
                attendees.append({"email": user.email})

        for user in interview.guests.all():
            user_list.append(user.user)
            attendees.append({"email": user.user.email})

        # email = vendor_account_manager(interview.submission.lead.vendor_company.name)
        # if email:
        #     attendees.append({"email": email})

        if interview.consultant.id == "948":
            attendees.append({"email": "jyothsna.consultadd@gmail.com"})
        return user_list, attendees
    except Exception as error:
        write_exception(error, request)
        return [], []


def date_filter(queryset, timestamp, field_str):
    filters = dict()
    if timestamp and type(timestamp) == dict:
        lte_date = timestamp.get('lte', None)
        if lte_date:
            lte_date = (
                    datetime.strptime(lte_date, '%Y-%m-%d').date() + timedelta(days=1)).strftime("%Y-%m-%d")
        lte = lte_date
        gte = timestamp.get('gte', None)
        if lte and gte and lte == gte:  # Check if lte and gte are the same date
            filters[f"{field_str}__date"] = lte  # Use "__date" for exact date matching
        else:
            if lte:
                filters[f"{field_str}__lte"] = lte
            if gte:
                filters[f"{field_str}__gte"] = gte
    return queryset.filter(**filters)


# Change status of scheduled and rescheduled Interviews to feedback_due
def change_to_feedback_due():
    try:
        """
            Updates the status of interviews and sends push notifications for feedback.

            - Retrieves interviews that have a start time earlier than or equal to the current UTC time
              and have a status of 'scheduled' or 'rescheduled'.
            - Updates the status of the retrieved interviews to 'feedback_due'.
            - Deletes push notifications for which there are no corresponding interviews with 'feedback_due' status.
            - Creates push notifications for supervisors associated with screenings in 'feedback_due' status.
            - Sends push notifications to supervisors with the necessary information.
            """
        tz = timezone('US/Eastern')
        time_est = datetime.now(tz).replace(tzinfo=timezone('UTC'))
        previous_interviews = Interview.objects.filter(end_time__lt=time_est, status__in=['scheduled', 'rescheduled'])
        for interview in previous_interviews:
            interview.status = 'feedback_due'
            interview.save()
            data = {
                "title": "interview feedback due",
                "category": "alert",
                "description": f"your {interview.submission.consultant_marketing.consultant.name} interview"
                               f" (I-{interview.id}) supervisor feedback is pending",
                "parent_type": "submission",
                "target_type": "interview",
                "parent_id": interview.submission.id,
                "target_id": interview.id,
                "sender_id": interview.supervisor.id,
                "recipient_user_type": "user",
                "sender_user_type": "user",
            }
            create_notification([interview.supervisor], data)

        # Deletes push notifications for which there are no corresponding interviews with 'feedback_due' status.
        if os.environ.get('ENV') == 'prod':
            delete_supervisor_notification.delay()

        # Creates push notifications for supervisors associated with screenings in 'feedback_due' status.
        interviews = Interview.objects.filter(
            start_time__gte=datetime.strptime("2022-05-04", "%Y-%m-%d"),
            end_time__lte=datetime.now(timezone('US/Eastern')).replace(tzinfo=timezone('UTC')) - timedelta(
                hours=4)
        ).exclude(
            status__in=["cancelled", "next_round", "offer", "failed", "scheduled", "rescheduled"]
        ).exclude(
            supervisor_feedback__question__form_name='interview'
        ).order_by('id').distinct('id')

        supervisor_ids = interviews.values_list('supervisor', flat=True).distinct()
        supervisor_list = User.objects.filter(id__in=supervisor_ids)

        for supervisor in supervisor_list:
            content_type = ContentType.objects.get(model='interview')
            notification, created = UserNotification.objects.get_or_create(user=supervisor, content_type=content_type)
            if created:
                notification.is_active=True
                notification.save()
                message_body = {
                    "body": "interview feedback due", "title": "interview feedback due", "category": "PopUp",
                    "data": {
                        'supervisor_id': supervisor.id,
                        'count': 1
                    },
                }
                registration_ids = list(
                    FCMDevice.objects.filter(
                        object_id=supervisor.id, content_type__model='user').values_list('device_id', flat=True))
                push_notification_consultant(registration_ids, message_body)

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
        is_consultant = interview.supervisor.employee_id == 9999 or False
        call_supervisor = interview.consultant.name if is_consultant else interview.supervisor.employee_name

        return f"Call Supervisor - {call_supervisor} " \
               f"{'(Consultant)' if is_consultant == True else ''} :: {interview.round}R :: " \
               f"{interview.get_screening_type_display()} :: {interview.get_interview_mode_display()} ::"\
               f"{interview.start_time.strftime('%m/%d/%Y :: %I:%M %p EST')} :: {interview.submission.client} ::"\
               f"{interview.consultant.name} :: {interview.marketer.employee_name} ::  {interview.submission.employer}"

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
            work_type=request.data['work_type'],

            consultant_marketing_id=request.data['marketing_id'],
            marketing_team_id=request.data.get('marketing_team_id', request.user.team.id),

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


def coder_request_notification(interview, title, request):
    try:
        payload = {
            "title": title,
            "interview": interview
        }
        slack.coder_request_card(payload, request)
        return "ok"
    except Exception as error:
        write_exception(error, request)
        return error, "error"


def test_received_notification(test, timezone, request):
    try:
        skills = ", ".join(skill.title() for skill in test.skills)
        if test.is_offline:
            test_data = "Offline"
        elif test.is_video:
            test_data = "Video"
        else:
            test_data = "Online"

        if type(test.deadline) == str:
            deadline = datetime.strptime(str(test.deadline), '%Y-%m-%d').strftime('%a, %d %B %Y')
        else:
            deadline = test.deadline.strftime('%a, %d %B %Y') if test.deadline else "NA"

        client = test.submission.client
        subtitle = f"*TST-{test.id}*: Received a *{test_data} {skills}* test from Unknown client for " \
                   f" *{test.submission.consultant.name}* "
        if client:
            if len(client) > 1:
                subtitle = f"*TST-{test.id}*: Received a *{test_data} {skills}* test from " \
                           f"*{test.submission.client.strip()}* for *{test.submission.consultant.name}* "

        activity_text = f"Requested by *{test.marketer.employee_name}* from *{test.marketer.team.name}*"
        payload = {
            "subtitle": subtitle, "activity_text": activity_text, "timezone": timezone, "deadline": deadline
        }
        # MessageCard.test_received_card(payload, request)
        return "ok"
    except Exception as error:
        write_exception(error, request)
        return str(error)


def structure_mail_data(data):
    single_questions = []
    parent_questions = []
    parent_questions_data = {}
    for item in data:
        if item['parent_question']:
            if item['parent_question'] not in parent_questions:
                parent_questions.append(item['parent_question'])
                parent_questions_data[item['parent_question']] = [item]
            else:
                parent_questions_data[item['parent_question']].append(item)
        else:
            single_questions.append(item)
    return single_questions, parent_questions_data


def create_answer(request, obj, model):
    try:
        ques_answers = []
        content_type = ContentType.objects.get(model=model)
        payload = json.loads(request.data.get('feedback_form'))
        for data in payload:
            question = get_object_or_404(Question, id=data['question_id'])
            if question.answer_type in ['no_remark', 'yes_remark', 'yes_attachment', 'no_attachment'] \
                    and data.get('comment') is not None:
                value = f'{data.get("answer")}: {data.get("comment")}'
            elif question.answer_type == 'multi_select':
                available_sets = set(question.options)
                answer = set(data.get("answer").replace(', ', ',').split(','))
                if answer.issubset(available_sets):
                    value = data.get("answer", None)
                else:
                    new_options = answer - available_sets
                    for option in new_options: question.options.append(option)
                    question.options.remove('None')
                    question.options.extend(['None'])
                    question.save()
                    value = data.get("answer", None)
            elif question.answer_type == 'option':
                value = data.get("answer")
                available_option = question.options
                if question.title == 'Platform':
                    test_platform(request, value)
                else:
                    if value not in available_option:
                        question.options.append(value)
                        question.save()
            else:
                value = data.get("answer", None)

            answer = Answer.objects.create(
                answer=value,
                object_id=obj.id,
                question=question,
                submitted_by=request.user,
                content_type=content_type,
                parent_question_id=data.get('parent_question_id', None)
            )
            attachment_id = f"{question.id}-{answer.parent_question_id}" if answer.parent_question else question.id
            if request.FILES.getlist(str(attachment_id)):
                for file in request.FILES.getlist(str(attachment_id)):
                    file_data = {
                        "file": file,
                        "model": "answer",
                        "object_id": answer.id,
                        "type": "test_feedback",
                        "creator": request.user,
                    }
                    create_attachment(file_data)
            ques_answers.append({
                "id": answer.id,
                "answer": data.get("answer"),
                "comment": data.get("comment"),
                "question": answer.question.title,
                "parent_question": answer.parent_question.title if answer.parent_question else None,
            })
        return ques_answers
    except Exception as error:
        write_info(message=error, function='create_answer')
        return str(error)


def interview_card_data(obj, request):
    try:
        interview_data = []
        supervisor_feedback = obj.supervisor_feedback.filter(
            question__form_name='interview').order_by('question__position')
        if supervisor_feedback:
            supervisor_feedback_data = []
            supervisor = obj.supervisor
            for feedback in supervisor_feedback:
                sup_feedback = {
                    "question": feedback.question.title,
                    "answer": feedback.answer,
                    "answer_type": feedback.question.answer_type
                }
                supervisor_feedback_data.append(sup_feedback)
            supervisor_feedback_data.insert(
                0, {"question": "Supervisor Name",
                    "answer": f"<@{supervisor.slack_id}>" if supervisor.slack_id else f"`{supervisor}`"}
            )
            sup_feedback = " \n ".join(
                f"*{feedback['question']}*:  {feedback['answer']}"
                if feedback.get('answer_type') != 'multi_select'
                else f"*{feedback['question']}*:  {feedback.get('answer', 'NA').replace('[', '').replace(']', '')}"
                for feedback in supervisor_feedback_data
            )
            supervisor_data = {"feedback": sup_feedback, "header": ":telephone_receiver: Supervisor Feedback"}
            interview_data.append(supervisor_data)

        coding_feedback = obj.supervisor_feedback.filter(
            question__form_name='coding').order_by('question_id').distinct('question_id')
        if coding_feedback or obj.coding_present is not None:
            coding_feedback_data = []
            for feedback in coding_feedback:
                coding_feedback = {
                    "answer": feedback.answer,
                    "question": feedback.question.title,
                    "answer_type": feedback.question.answer_type
                }
                coding_feedback_data.append(coding_feedback)
            guest = " ".join([
                f"`<@{i.user.slack_id}>`" if i.user.slack_id else f"`{i.user.employee_name}`"
                for i in obj.guests.filter(type__in=['Coder', 'Coder & Assistant', 'Assistant'])
            ])
            coding_feedback_data.insert(0, {"question": "Coders Name", "answer": guest if guest else "NA"})
            coding_feedback_data.insert(
                1, {"question": "Coding Present", "answer": "Yes" if obj.coding_present else "No"}
            )
            coding_feedback_data.append(
                {"question": "Feedback", "answer_type": "long_text",
                 "answer": obj.guest_remark if obj.guest_remark else "NA"}
            )
            coder_feedback = " \n ".join(
                f"*{feedback['question']}*:  {feedback['answer']}"
                if feedback.get('answer_type') != 'multi_select'
                else f"*{feedback['question']}*:  {feedback.get('answer', 'NA').replace('[', '').replace(']', '')}"
                for feedback in coding_feedback_data)
            coders_data = {"feedback": coder_feedback, "header": " :computer: Coder Feedback"}
            interview_data.append(coders_data)

        interview_data.append({"feedback": obj.feedback, "header": ":lower_left_fountain_pen:  Vendor/Client Feedback"})
        return interview_data
    except Exception as error:
        write_exception(error, request)


def interview_feedback_card(obj, request):
    try:
        interview_data = interview_card_data(obj, request)
        slack_card_data = slack.interview_feedback_card(obj, interview_data, request)
        return slack_card_data
    except Exception as error:
        write_exception(error, request)


def get_authenticated_users(request, get_id=False):
    try:
        authenticated_users = list()
        if get_id:
            authenticated_users.append(request.user.id)
            authenticated_users.extend(request.user.handovers.all().values_list('user__id', flat=True))
        else:
            authenticated_users.append(request.user)
            for handover in request.user.handovers.all():
                authenticated_users.append(handover.user)
        return authenticated_users
    except Exception as error:
        write_exception(error, request)


def get_interview_report(payload, request):
    try:
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow([
            "Interview Id", "Consultant Name", "Marketer Name", "Supervisor Name", "Client Name", "Vendor Name",
            "Call Type", "Round", "Scheduled At", "Mode", "Screening Type", "Tech Stack", "Status", "Failure Reason",
            "Passed Reason"
        ])
        for data in payload:
            writer.writerow([
                data.get('id', None), data.get('consultant_name', None),
                data.get('submission').get('marketer_name', None),
                f"{data.get('supervisor_detail').get('supervisor_name')}"
                f"({data.get('supervisor_detail').get('call_given_by')})",
                data.get('submission').get('client', None), data.get('submission').get('vendor', None),
                data.get('call_type'), data.get('round', None), data.get('start_time', None),
                data.get('interview_mode', None), data.get('screening_type', None), data.get('tech_stack', None),
                data.get('status', None), data.get('failure_reason', None), data.get('passed_reason', None)
            ])
        return response
    except Exception as error:
        write_exception(error, request)


def test_platform(request, platform):
    try:
        test_content_type = ContentType.objects.get(model='test')
        question = get_object_or_404(Question, title='Platform')
        available_option = question.options
        available_platforms = Choice.objects.filter(
            name__icontains=platform, field='platform',
            content_type=test_content_type, display_name__icontains=platform
        )
        if not available_platforms.first() and platform != 'Not Available':
            Choice.objects.create(
                content_type=test_content_type, name=platform, field='platform',
                display_name=platform
            )
        if platform not in available_option:
            question.options.append(platform)
            question.save()
    except Exception as error:
        write_exception(error, request)


@shared_task()
def delete_supervisor_notification():
    try:
        content_type = ContentType.objects.get(model='interview')
        notifications = UserNotification.objects.filter(content_type=content_type)
        for notification in notifications:
            interviews = Interview.objects.filter(status="feedback_due", supervisor=notification.user)
            if not interviews:
                notification.delete()
    except Exception as error:
        write_exception(error, None)
        return str(error), False


def add_interviewer_profiles(obj, request):
    try:
        interviewers_profiles = request.data.get('interviewer_profiles', [])
        for interviewer in interviewers_profiles:
            if interviewer.get('id', None):
                interviewer_obj = get_object_or_404(InterviewerProfile, id=interviewer.get('id'))
                obj.interviewers.add(interviewer_obj)
            else:
                interviewer_obj = InterviewerProfile.objects.create(
                    name=interviewer.get('name'), email=interviewer.get('email', None),
                    created_by=request.user, linkedin=interviewer.get('linkedin', None), client=obj.submission.client
                )
            obj.interviewers.add(interviewer_obj)
            obj.save()
        return True
    except Exception as error:
        write_exception(error, request)
        return str(error)


def update_interviewer_profiles(obj, request):
    try:
        updated_interviewers = set()
        client = obj.submission.client
        interviewers_profiles = request.data.get('interviewer_profiles')
        existing_interviewers = set(obj.interviewers.all())
        for interviewer in interviewers_profiles:
            if interviewer.get('id', None):
                interviewer_obj = get_object_or_404(InterviewerProfile, id=interviewer.get('id'))
                serializer = InterviewerProfileSerializer(interviewer_obj, data=interviewer, partial=True)
                if not serializer.is_valid():
                    return Response(
                        {"message": "Interviewers details are incorrect", "error": str(serializer.errors)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                serializer.save()
                updated_interviewers.add(interviewer_obj)
            else:
                interviewer_obj = InterviewerProfile.objects.create(
                    name=interviewer.get('name'), email=interviewer.get('email', None),
                    created_by=request.user, linkedin=interviewer.get('linkedin', None), client=client
                )
                obj.interviewers.add(interviewer_obj)
                obj.save()
        existing_interviewers.difference_update(updated_interviewers)
        if existing_interviewers:
            removed_interviewers = [elm for elm in existing_interviewers]
            obj.interviewers.remove(*removed_interviewers)
            obj.save()
        return True
    except Exception as error:
        write_exception(error, request)
        return False


def get_guest_type(request):
    coding_required = request.data.get('coding')
    assistance_required = request.data.get('assistance')

    if coding_required and not assistance_required:
        guest_type = "Coder"
    elif not coding_required and assistance_required:
        guest_type = "Assistance"
    elif coding_required and assistance_required:
        guest_type = "Coder & Assistance"
    else:
        guest_type = "Not Required"
    return guest_type


def add_or_update_guest(obj, request, guests=[]):
    try:
        resp = 'Not Assigned'
        updated_guests = set()
        existing_guest = set(obj.guests.all())
        if not guests:
            guests = request.data.get('guest_info', [])
        for guest in guests:
            if guest.get('user_id', None) is None:
                continue
            guest_obj = GuestInfo.objects.filter(user_id=guest.get('user_id'), type=guest.get('type', None)).first()
            if not guest_obj:
                try:
                    user_guest = get_object_or_404(User, id=guest.get('user_id'))
                except ObjectDoesNotExist:
                    return Response({"message": "Guest does not exist"}, status=status.HTTP_400_BAD_REQUEST)
                guest_obj = GuestInfo.objects.create(user=user_guest, type=guest.get('type', None))
            if guest_obj not in existing_guest:
                obj.guests.add(guest_obj)
                obj.save()
                resp = 'assigned'
            updated_guests.add(guest_obj)

        existing_guest.difference_update(updated_guests)
        if existing_guest:
            remove_guests = [elm for elm in existing_guest]
            obj.guests.remove(*remove_guests)
            obj.save()
        return resp
    except Exception as error:
        write_exception(error, request)
        return False


def check_updated_value(pre_value, updated_value, key_name):
    if pre_value != updated_value:
        return key_name
    return None


def check_guest(data, guest_type):
    if guest_type == 'coder':
        types = ['Coder', 'Coder & Assistant']
    else:
        types = ['Assistant', 'Coder & Assistant']
    for user in data:
        if user.get('type') in types:
            return True
    return False
