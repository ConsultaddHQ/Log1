import json
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import ContentType

from constance import config
from employee.models import User
from consultant.models import ConsultantProfile
from attachment.models import create_attachment
from log1.utils import write_info, write_exception
from utils_app.slack_notification import MessageCard as slack
from utils_app.teams_notification import MessageCard as teams
from marketing.models import Submission, Interview, Question, Answer


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
        attendees = [{'email': interview.supervisor.email}, {'email': interview.submission.created_by.email}]
        if 'engineer' not in request.user.roles:
            scrum_masters = User.objects.filter(
                team=request.user.team, role__name__in=['admin', 'proxy'], account_login=True
            )
            for user in scrum_masters:
                user_list.append(user)
                attendees.append({"email": user.email})

        for user in interview.guest.all():
            user_list.append(user)
            attendees.append({"email": user.email})

        email = vendor_account_manager(interview.submission.lead.vendor_company.name)
        if email:
            attendees.append({"email": email})

        return user_list, attendees
    except Exception as error:
        write_exception(error, request)
        return [], []


def date_filter(queryset, timestamp, field_str):
    filters = dict()
    if timestamp and type(timestamp) == dict:
        lte = timestamp.get('lte', None)
        gte = timestamp.get('gte', None)
        if lte:
            filters[f"{field_str}__lt"] = lte
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


def coder_request_notification(interview, title, request):
    try:
        payload = {
            "title": title,
            "interview": interview
        }
        slack.coder_request_card(payload, request)
        teams.coder_request_card(payload, request)
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


def get_display_choice(data, data_type, request):
    try:
        if data_type == 'interview_mode':
            for mode in Interview.INTERVIEW_MODE:
                if data == mode[0]:
                    return mode[1]
            return None
        if data_type == 'screening_type':
            for mode in Interview.TYPE_CHOICES:
                if data == mode[0]:
                    return mode[1]
            return None
    except Exception as error:
        write_exception(error, request)
        return str(error)


def interview_card_data(obj, request):
    try:
        interview_data = []
        container_names = []
        coding_feedback_data = []
        supervisor_feedback_data = []
        interview_info = [
            {
                "question": "Interview ID",
                "answer": f"I-{obj.id}"
            },
            {
                "question": "Consultant Name",
                "answer": obj.consultant.name
            },
            {
                "question": "Client",
                "answer": obj.submission.client
            },
            {
                "question": "Technology",
                "answer": obj.submission.lead.job_title if obj.submission.lead.job_title else "NA"
            },
            {
                "question": "Round",
                "answer": f"{obj.round if obj.round else 'NA'}"
            },
            {
                "question": "Mode",
                "answer": get_display_choice(obj.interview_mode, 'interview_mode', request),
            },
            {
                "question": "Screening Type",
                "answer": get_display_choice(obj.screening_type, 'screening_type', request)
            },
            {
                "question": "Marketer",
                "answer": obj.marketer.employee_name
            },
            {
                "question": "Recruiter",
                "answer": obj.consultant.recruiter.employee_name
            },
            {
                "question": "Team",
                "answer": obj.submission.created_by.team.name
            },
            {
                "question": "Date",
                "answer": obj.start_time.date().strftime("%m/%d/%Y")
            },
            {
                "question": "Time",
                "answer": obj.start_time.time().strftime("%H:%M")
            },
        ]
        interview_data.append(interview_info)
        emoji = ''
        if obj.status == 'next_round':
            emoji = ':+1:'
        elif obj.status == 'failed':
            emoji = ':-1:'
        if obj.status == 'offer':
            emoji = ':v:'
        container_names.append(f"{emoji} Interview Feedback")

        coding_feedback = obj.supervisor_feedback.filter(
            question__form_name='coding').order_by('question_id').distinct('question_id')
        if coding_feedback or obj.coding_present is not None:
            for feedback in coding_feedback:
                coding_feedback = {
                    "answer": feedback.answer
                    if feedback.question.answer_type != 'multi_select' else "\n".join(feedback.answer.split(", ")),
                    "question": feedback.question.title,
                    "answer_type": feedback.question.answer_type
                }
                coding_feedback_data.append(coding_feedback)
            guest = "\n".join([i.employee_name for i in obj.guest.all()])
            coding_feedback_data.insert(0, {"question": "Coder's name", "answer": guest if guest else "NA"})
            coding_feedback_data.insert(
                1, {"question": "Coding Present", "answer": "Yes" if obj.coding_present else "No"}
            )
            coding_feedback_data.append(
                {"question": "Feedback", "answer_type": "long_text",
                 "answer": obj.guest_remark if obj.guest_remark else "NA"}
            )
            interview_data.append(coding_feedback_data)
            container_names.append(":computer: Coder's Feedback")

        supervisor_feedback = obj.supervisor_feedback.filter(
            question__form_name='interview').order_by('question__position')
        if supervisor_feedback:
            for feedback in supervisor_feedback:
                sup_feedback = {
                    "question": feedback.question.title,
                    "answer": feedback.answer
                    if feedback.question.answer_type != 'multi_select' else "\n".join(feedback.answer.split(", ")),
                    "answer_type": feedback.question.answer_type
                }
                supervisor_feedback_data.append(sup_feedback)
            supervisor_feedback_data.insert(
                0, {"question": "Supervisor Name", "answer": obj.supervisor.employee_name}
            )
            interview_data.append(supervisor_feedback_data)
            container_names.append(":telephone_receiver: Supervisor's Feedback")

        status = "NA"
        for i in obj.STATUS_CHOICES:
            if i[0] == obj.status:
                status = i[1]
        marketer_feedback_data = [
            {"question": "Status", "answer": status, "answer_type": "long_text"},
            {"question": "Feedback", "answer": obj.feedback, "answer_type": "long_text"}
        ]
        interview_data.append(marketer_feedback_data)
        container_names.append(":lower_left_fountain_pen: Vendor/Client's Feedback")

        return interview_data, container_names
    except Exception as error:
        write_exception(error, request)


def interview_feedback_card(obj, request):
    try:
        interview_data, header_names = interview_card_data(obj, request)
        card_data = slack.interview_feedback_card(interview_data=interview_data, header_names=header_names, request=request)
        card_data = teams.interview_feedback_card(interview_data=interview_data, header_names=header_names, request=request)
        return card_data
    except Exception as error:
        write_exception(error, request)
