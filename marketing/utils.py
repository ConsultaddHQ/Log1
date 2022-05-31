import json
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import ContentType

from constance import config
from employee.models import User
from consultant.models import ConsultantProfile
from attachment.models import create_attachment
from marketing.models import Submission, Interview, Question, Answer
from utils_app.calendar import get_profile_picture
from log1.utils import write_info, write_exception, post_msg_using_webhook


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

        return f"""Call Supervisor - {call_supervisor}
            {'(Consultant)' if is_consultant == True else ""} :: {interview.round}R :: 
            {interview.get_screening_type_display()} :: {interview.get_interview_mode_display()} :: 
            {interview.start_time.strftime('%m/%d/%Y :: %I:%M %p EST')} :: {interview.submission.client} :: 
            {interview.consultant.name} :: {interview.marketer.employee_name} ::  {interview.submission.employer}"""
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


def coder_request_notification(user, interview, title):
    try:
        profile_path = get_profile_picture(user)
        data = {
            "@type": "MessageCard",
            "themeColor": "#0076D7",
            "@context": "http://schema.org/extensions",
            "summary": f"Coding assignment",
            "sections": [
                {
                    "activityTitle": title,
                    "activitySubtitle": f"I-{interview.id} : Interview from ***{interview.submission.client}*** for "
                                        f"***{interview.submission.consultant.name}*** ",
                    "activityText": f"Requested by ***{interview.submission.created_by.employee_name}*** from "
                                    f"***{interview.submission.created_by.team.name}***",
                    "activityImage": profile_path,
                    "facts": [
                        {
                            "name": f"Technology",
                            "value": f"{interview.tech_stack}"
                        },
                        {
                            "name": f"Supervisor",
                            "value": f"{interview.supervisor.employee_name}"
                        },
                        {
                            "name": f"Date",
                            "value": f"{interview.start_time.strftime('%a, %d %B %Y')}"
                        },
                        {
                            "name": f"Time",
                            "value": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                     f"{interview.end_time.strftime('%I:%M %p EST')}"
                        }
                    ],
                    "markdown": True
                }
            ]
        }
        post_msg_using_webhook(config.engineering_url, data)
        return "ok"
    except Exception as error:
        write_info(message=error, function='coder_request_notification')
        return str(error)


def coder_assigned_notification(user, interview):
    try:
        profile_path = get_profile_picture(user)
        coding_experts = ", ".join(interview.guest.all().values_list('employee_name', flat=True))
        data = {
            "@type": "MessageCard",
            "themeColor": "#0076D7",
            "@context": "http://schema.org/extensions",
            "summary": f"Coding expert request for Interview ",
            "sections": [
                {
                    "activityTitle": "Coding assignment",
                    "activitySubtitle": f"I-{interview.id} : Interview from ***{interview.submission.client}*** for "
                                        f" ***{interview.submission.consultant.name}*** ",
                    "activityText": f"Requested by ***{interview.submission.created_by.employee_name}*** from "
                                    f"***{interview.submission.created_by.team.name}***",
                    "activityImage": profile_path,
                    "facts": [
                        {
                            "name": "Technology",
                            "value": str(interview.tech_stack)
                        },
                        {
                            "name": "Supervisor",
                            "value": str(interview.supervisor.employee_name)
                        },
                        {
                            "name": "Date",
                            "value": str(interview.start_time.strftime('%a, %d %B'))
                        },
                        {
                            "name": "Time",
                            "value": f"{interview.start_time.strftime('%I:%M %p EST')} - "
                                     f"{interview.end_time.strftime('%I:%M %p EST')}"
                        },
                        {
                            "name": "Coding Expert",
                            "value": coding_experts
                        }
                    ],
                    "markdown": True
                }
            ]
        }
        post_msg_using_webhook(config.engineering_url, data)
        return "ok"
    except Exception as error:
        write_info(message=error, function='coder_request_notification')
        return str(error)


def test_received_notification(user, test, timezone):
    try:
        skills = ", ".join(skill.title() for skill in test.skills)
        profile_path = get_profile_picture(user)
        if test.is_offline:
            test_data = "Offline"
        elif test.is_video:
            test_data = "Video"
        else:
            test_data = "Online"

        if type(test.deadline) == str:
            deadline = datetime.strptime(str(test.deadline), '%Y-%m-%d').strftime('%a, %d %B %Y')
        else:
            deadline = test.deadline.strftime('%a, %d %B %Y')

        client = test.submission.client
        subtitle = f"***TST-{test.id}***: Received a ***{test_data} {skills}*** test from Unknown client for " \
                   f" ***{test.submission.consultant.name}*** "
        if client:
            if len(client) > 1:
                subtitle = f"***TST-{test.id}***: Received a ***{test_data} {skills}*** test from " \
                           f"***{test.submission.client.strip()}*** for ***{test.submission.consultant.name}*** "

        activity_text = f"Requested by ***{test.marketer.employee_name}*** from ***{test.marketer.team.name}***"
        data = {
            "@type": "MessageCard",
            "themeColor": "#0076D7",
            "@context": "http://schema.org/extensions",
            "summary": f"Coding expert request for Interview ",
            "sections": [
                {
                    "activitySubtitle": subtitle,
                    "activityImage": profile_path,
                    "activityText": activity_text,
                    "activityTitle": "Test Received",
                    "facts": [
                        {
                            "name": "Timezone",
                            "value": timezone
                        },
                        {
                            "name": "Deadline",
                            "value": deadline
                        }
                    ],
                    "markdown": True
                }
            ]
        }
        post_msg_using_webhook(config.engineering_url, data)
        return "ok"
    except Exception as error:
        write_info(message=error, function='test_received_notification')
        return str(error)


def sup_feedback_notification(title, obj):
    try:
        supervisor = obj.supervisor
        profile_path = get_profile_picture(supervisor) if supervisor else None
        data = {
            "@type": "MessageCard",
            "themeColor": "#0076D7",
            "@context": "http://schema.org/extensions",
            "summary": f"Supervisor feedback for interview",
            "sections": [
                {
                    "activityImage": profile_path,
                    "activityTitle": "Supervisor Feedback",
                    "activitySubtitle": f"***{title}***",
                    "facts": [],
                    "markdown": True
                }
            ]
        }

        ques_answers = obj.supervisor_feedback.order_by('question_id').distinct('question_id')
        for ques_ans in ques_answers:
            answer = ques_ans.answer
            if answer == 'True':
                answer = "Yes"
            elif answer == 'False':
                answer = "No"
            elif '[' in answer:
                answer = answer.replace(']', '').replace('[', '').replace('"', '')
            data['sections'][0]["facts"].append({
                "name": ques_ans.question.title,
                "value": answer
            })

        post_msg_using_webhook(config.interview_feedback_url, data)
        return "ok"
    except Exception as error:
        write_info(message=error, function='sup_feedback_notification')
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
                all_data = json.loads(data.get("answer", '[]'))
                value = ", ".join(item for item in all_data)
            else:
                value = data.get("answer", None)

            answer = Answer.objects.create(
                answer=value,
                question=question,
                object_id=obj.id,
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
