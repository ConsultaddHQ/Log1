import os
import json
from pytz import timezone
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from constance import config
from employee.models import User
from utils_app.models import Choice
from consultant.models import Consultant
from activity.views import create_activity
from utils_app.thred_mail import send_email
from utils_app.mailing import send_email as mail
from consultant.utils import send_notification_for_user
from log1.utils import password_generator, write_exception
from utils_app.slack_notification import MessageCard as slack
from engineering.models import TrainingCheckList, ProjectDescription
from project.models import Project, TimeSheet, ConsultantLeave, TimetrackEvent


def set_consultant_password(consultant):
    try:
        if not consultant.is_active:
            password = password_generator(password_length=10, strength=3)
            consultant.set_password(password)
            consultant.is_active = True
            consultant.save()
            return password, True
        return "password", False
    except Exception as error:
        write_exception(message=error)


def create_remote_consultant(request):
    try:
        remote_consultant_id = request.data.get('remote_consultant_id', None)
        consultant = None
        if remote_consultant_id:
            if request.data.get("remote_consultant_type", None) == 'user':
                qs = User.objects.filter(id=remote_consultant_id)
                if not qs:
                    write_exception(message=f"User not found with ID {remote_consultant_id}")
                    return None
                user = qs.first()
                consultant, _ = Consultant.objects.get_or_create(email=user.email)
                consultant.is_active = True
                consultant.remote_only = True
                consultant.gender = user.gender
                consultant.name = user.employee_name
                consultant.save()
            else:
                consultant = get_object_or_404(Consultant, id=remote_consultant_id)
        return consultant
    except Exception as error:
        write_exception(message=error)


def get_attachment_status(project):
    s_msa, s_work_order, offer_letter = 0, 0, 0
    sub = project.submission

    start_date = 1 if project.start_date else 0
    client_address = 1 if (project.client_address and len(project.client_address.strip()) > 0) else 0
    vendor_address = 1 if (project.vendor_address and len(project.vendor_address.strip()) > 0) else 0
    reporting_details = 1 if (project.reporting_details and len(project.reporting_details.strip()) > 0) else 0

    if project.submission.get_work_type_display() != 'C2C':
        if project.attachments.filter(attachment_type='offer_letter'):
            offer_letter = 1

        total = offer_letter + client_address + vendor_address + start_date + reporting_details
        if sub.consultant.name == 'Bharat Bhate' and sub.created_by.employee_id == 2831:
            list_status = True
        else:
            list_status = True if (total / 5) >= 1 else False

        return {
            "total": total,
            "status": list_status,
            "start_date": start_date,
            "offer_letter": offer_letter,
            "client_address": client_address,
            "vendor_address": vendor_address,
            "reporting_details": reporting_details,
        }

    if project.attachments.filter(attachment_type='msa_signed'):
        s_msa = 1

    if project.attachments.filter(attachment_type='work_order_signed'):
        s_work_order = 1

    if project.attachments.filter(attachment_type='work_order_msa_signed'):
        s_msa, s_work_order = 1, 1

    total = s_msa + s_work_order + client_address + vendor_address + start_date + reporting_details
    if sub.consultant.name == 'Bharat Bhate' and sub.created_by.employee_id == 2831:
        list_status = True
    else:
        list_status = True if (total / 6) >= 1 else False
    return {
        "total": 6,
        "msa_signed": s_msa,
        "status": list_status,
        "start_date": start_date,
        "client_address": client_address,
        "vendor_address": vendor_address,
        "work_order_signed": s_work_order,
        "reporting_details": reporting_details,
    }


def get_project_check_list(project):
    msa, work_order, offer_letter = 0, 0, 0

    if project.submission.get_work_type_display() != 'C2C':
        if project.attachments.filter(attachment_type='offer_letter'):
            offer_letter = 1
        result = get_attachment_status(project)

        return {
            "total": 5,
            "status": result.get("status"),
            "start_date": result.get("start_date"),
            "offer_letter": result.get("offer_letter"),
            "client_address": result.get("client_address"),
            "vendor_address": result.get("vendor_address"),
            "reporting_details": result.get("reporting_details"),
        }

    if project.submission.get_work_type_display() != 'C2C':
        result = get_attachment_status(project)

        return {
            "total": 5,
            "status": result.get("status"),
            "start_date": result.get("start_date"),
            "offer_letter": result.get("offer_letter"),
            "client_address": result.get("client_address"),
            "vendor_address": result.get("vendor_address"),
            "reporting_details": result.get("reporting_details"),
        }

    if project.submission.get_work_type_display() != 'C2C':
        result = get_attachment_status(project)

        return {
            "total": 5,
            "status": result.get("status"),
            "start_date": result.get("start_date"),
            "offer_letter": result.get("offer_letter"),
            "client_address": result.get("client_address"),
            "vendor_address": result.get("vendor_address"),
            "reporting_details": result.get("reporting_details"),
        }

    if project.attachments.filter(attachment_type='msa'):
        msa = 1
    if project.attachments.filter(attachment_type='work_order'):
        work_order = 1
    if project.attachments.filter(attachment_type='work_order_msa'):
        msa, work_order = 1, 1
    result = get_attachment_status(project)

    return {
        "total": 6,
        "msa": msa,
        "work_order": work_order,
        "status": result.get("status"),
        "msa_signed": result.get("msa_signed"),
        "start_date": result.get("start_date"),
        "client_address": result.get("client_address"),
        "vendor_address": result.get("vendor_address"),
        "work_order_signed": result.get("work_order_signed"),
        "reporting_details": result.get("reporting_details"),
    }


def fetch_project_status():
    other_status = ['new', 'other', 'joined', 'received', 'signed', 'extended', 'on_boarded', 'complete']
    cancellation_status = [
        'cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled', 'cancelled-contract_conflicts',
        'cancelled-candidate_denied', 'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
        'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location'
    ]
    termination_status = [
        'terminated', 'terminated-resigned', 'terminated-resigned_rate_issue', 'terminated-fired_performance_issue',
        'terminated-resigned_technology_issue', 'terminated-fired_budget_issue', 'terminated-fired_security_issue',
        'terminated-resigned_location_issue', 'terminated-fired', 'terminated-resigned_full_time_offer'
    ]
    return cancellation_status + termination_status + other_status, cancellation_status, termination_status


def diff_month_days(start, end):
    if type(start) == str:
        start = datetime.strptime(str(start), '%Y-%m-%d')
    if type(end) == str:
        end = datetime.strptime(str(end), '%Y-%m-%d')
    return (end.year - start.year) * 12 + end.month - start.month


class ProjectUtil:
    def __init__(self, project, request=None):
        self.request = request
        self.project = project
        self.project_end = None
        self.user = request.user
        self.statuses = fetch_project_status()
        self.consultant = project.submission.consultant_marketing.consultant
        self.project_start = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%a, %d %B %Y')
        if project.end_date:
            self.project_end = datetime.strptime(str(project.end_date), '%Y-%m-%d').strftime('%a, %d %B %Y')
        if self.project.employer:
            self.employer = self.project.employer
        else:
            self.employer = self.project.submission.employer
        marketer = self.project.submission.created_by
        marketer_name = f"<@{marketer.slack_id}>" if marketer.slack_id else marketer.employee_name
        self.activity_text = f"Project by *{marketer_name}* from *{marketer.team.name}*"

    def fetch_project_count(self, project_status):
        try:
            team = self.project.submission.marketing_team
            day_one = datetime.today().replace(day=1, hour=0, minute=0)
            total_count = Project.objects.filter(
                statuses__status=project_status, statuses__created__gte=day_one
            ).count()
            team_count = Project.objects.filter(
                statuses__status=project_status,
                statuses__created__gte=day_one,
                submission__marketing_team=team,
            ).count()
            return total_count, team_count, team.name
        except Exception as error:
            write_exception(message=error, request=self.request)

    def fetch_project_termination_count(self):
        try:
            team = self.project.submission.marketing_team
            day_one = datetime.today().replace(day=1, hour=0, minute=0)
            total_count = Project.objects.filter(
                statuses__status__istartswith="terminated", statuses__created__gte=day_one
            ).count()
            team_count = Project.objects.filter(
                statuses__created__gte=day_one,
                submission__marketing_team=team,
                statuses__status__istartswith="terminated"
            ).count()
            return total_count, team_count, team.name
        except Exception as error:
            write_exception(message=error, request=self.request)

    def send_join_notification(self):
        try:
            recruiter_name = "NA"
            recruiter = self.consultant.recruiter
            total, team_count, team = self.fetch_project_count("joined")
            # team_name = self.project.submission.created_by.team.name
            if recruiter:
                recruiter_name = self.consultant.recruiter.employee_name

            if self.project.is_remote or self.project.submission.lead.is_w2:
                activity_title = f"*{self.project.consultant.name.strip()}* joined *Remote* project at " \
                                 f"*{self.project.submission.client}* on *{self.project_start}* as a " \
                                 f"*{self.project.submission.lead.job_title.strip()}*"
            else:
                activity_title = f"*{self.consultant.name.strip()}* joined project at " \
                                 f"*{self.project.submission.client}* on *{self.project_start}* as a " \
                                 f"*{self.project.submission.lead.job_title.strip()}*"

            payload = {
                "submission_id": self.project.submission.id, "project_id": self.project.id,
                "activity_title": activity_title, "activity_text": self.activity_text, "total": total,
                "employer": self.employer, "recruiter_name": recruiter_name, "team_name": team, "team": team_count,
                "submitted_on": datetime.strptime(str(self.project.submission.created).split(' ')[0],
                                                  '%Y-%m-%d').strftime('%a, %d %B %Y'),
            }
            slack.consultant_joined_message_card(payload, self.request)
            title = f" Project Joined :: {self.consultant.name} :: {self.project.submission.client}"
            send_notification_for_user(self.consultant, self.user, title, 'project')
        except Exception as error:
            write_exception(message=error, request=self.request)

    def send_receive_notification(self):
        try:
            recruiter_name = "NA"
            recruiter = self.consultant.recruiter
            if recruiter:
                recruiter_name = f"<@{recruiter.slack_id}>" if recruiter.slack_id else recruiter.employee_name

            total, team_count, team = self.fetch_project_count("received")
            interviews = self.project.submission.screening.exclude(status='cancelled')
            supervisors = ", ".join([f"Round {interview.round} - <@{interview.supervisor.slack_id}>"
                                     if interview.supervisor.slack_id else interview.supervisor.employee_name
                                    if interview.supervisor.employee_id != 9999
                                    else self.project.submission.consultant.name
                                     for interview, count in zip(interviews, range(0, len(interviews)))
                                     if interview.supervisor])

            payload = {
                "client": self.project.submission.client, "consultant": self.consultant.name,
                "city": self.project.city, "supervisors": supervisors,  "project_id": self.project.id,
                "activity_text": self.activity_text, "total": total, "employer": self.employer, "team": team,
                "recruiter_name": recruiter_name, "project_start": self.project_start, "team_count": team_count,
                "submission_id": self.project.submission.id, "job_title": self.project.submission.lead.job_title,
            }
            slack.po_receive_message_card(payload, self.request)

            title = f" Project Received :: {self.consultant.name} :: {self.project.submission.client}"
            send_notification_for_user(self.consultant, self.user, title, "project")
        except Exception as error:
            write_exception(message=error, request=self.request)

    def send_termination_notification(self, status):
        try:
            recruiter_name = "NA"
            recruiter = self.consultant.recruiter
            total, team_count, team = self.fetch_project_termination_count()
            if recruiter:
                recruiter_name = f"<@{recruiter.slack_id}>" if recruiter.slack_id else recruiter.employee_name

            months = diff_month_days(self.project.start_date, self.project.end_date)
            reason = self.project.feedback if self.project.feedback else "Not updated on Log1"
            activity_sub_title = f"*{self.consultant.name.strip()}'s* project as a " \
                                 f"*{self.project.submission.lead.job_title.strip()}*, terminated from " \
                                 f"*{self.project.submission.client}* with the end date of *{self.project_end}*"

            payload = {
                "recruiter_name": recruiter_name, "status": status, "reason": reason,
                "sub_title": activity_sub_title, "activity_text": self.activity_text, "team": team,
                "months": months, "employer": self.employer, "city": self.project.city, "total": total,
                "submission_id": self.project.submission.id, "project_id": self.project.id, "team_count": team_count
            }
            slack.po_termination_message_card(payload, self.request)

            title = f"Project Terminated :: {self.consultant.name} :: {self.project.submission.client}"
            send_notification_for_user(self.consultant, self.user, title, 'project')
        except Exception as error:
            write_exception(message=error, request=self.request)

    def send_cancellation_notification(self, status):
        try:
            recruiter_name = "NA"
            recruiter = self.consultant.recruiter
            if recruiter:
                recruiter_name = self.consultant.recruiter.employee_name

            reason = self.project.feedback if self.project.feedback else "Not updated on Log1"

            activity_sub_title = f"*{self.consultant.name.strip()}'s* project as a " \
                                 f"*{self.project.submission.lead.job_title.strip()}*, cancelled at " \
                                 f"*{self.project.submission.client.strip()}*"
            payload = {
                "activity_text": self.activity_text, "submission_id": self.project.submission.id,
                "employer": self.employer, "recruiter_name": recruiter_name, "project_id": self.project.id,
                "status": status, "reason": reason, "activity_sub_title": activity_sub_title, "city": self.project.city
            }
            slack.po_cancellation_message_card(payload, self.request)

            title = f"Project Cancelled :: {self.consultant} :: {self.project.submission.client}"
            send_notification_for_user(self.project.consultant, self.user, title, 'project')
        except Exception as error:
            write_exception(message=error, request=self.request)

    def send_completion_notification(self):
        try:
            title = f" Project Completed :: {self.consultant} :: {self.project.submission.client}"
            send_notification_for_user(self.consultant, self.user, title, 'project')
        except Exception as error:
            write_exception(message=error, request=self.request)

    def create_timesheet(self):
        try:
            start_date = datetime.strptime(str(self.project.start_date), '%Y-%m-%d')
            week_day = start_date.weekday()
            if week_day == 0:
                end_date = start_date + timedelta(days=6)
            else:
                end_date = start_date + timedelta(days=6 - week_day)

            for i in range(2):
                TimeSheet.objects.get_or_create(
                    start=start_date, end=end_date,
                    hours=0, status='draft', project=self.project,
                )
                start_date = end_date + timedelta(days=1)
                end_date = end_date + timedelta(days=7)
        except Exception as error:
            write_exception(message=error, request=self.request)

    def assign_leave(self):
        try:
            consultant = self.project.consultant
            already_assigned = ConsultantLeave.objects.filter(consultant=consultant)
            if already_assigned:
                return None
            choices = Choice.objects.filter(content_type__model='consultantleave', field='leave')
            for choice in choices:
                ConsultantLeave.objects.create(
                    consultant=consultant, leave_type=choice, granted=0.0, balance=0.0, is_expired=False, year=2022
                )
            return "leave Assigned"
        except Exception as error:
            write_exception(message=error, request=self.request)
            return error, "error"


def fetch_scrum_masters(user):
    scrum_masters = list(User.objects.filter(
        team=user.team, role__name__in=['admin', 'proxy'], account_login=True
    ).values_list('email', flat=True))
    return scrum_masters


def send_support_mail(project, support, request):
    try:
        submission = project.submission
        consultant = project.submission.consultant
        recruiter = consultant.recruiter
        retention = consultant.relation
        to = [submission.created_by.email]

        cc = [config.RECRUITMENT, config.RELATIONS] + fetch_scrum_masters(submission.created_by)
        if recruiter:
            cc.append(recruiter.email)
        if retention:
            cc.append(retention.email)

        project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')

        mail_data = {
            'to': to, 'cc': cc, 'bcc': [],
            'template': '../templates/support.html',
            'subject': f"Initiate support for {consultant.name} :: {submission.client} :: {support.employee_name}",
            'context': {
                'marketer_name': submission.created_by.employee_name,
                'location': submission.lead.city, 'job_title': submission.lead.job_title,
                'consultant_phone_no': consultant.phone_no, 'start': project_start_date,
                'consultant_name': consultant.name, 'consultant_email': consultant.email,
                'client_name': submission.client, 'support_email': support.email, 'support_name': support.name
            },
        }

        res = "Development Server"
        if os.environ.get('ENV', 'local') == 'prod':
            res, msg, _ = send_email(mail_data, support.email, request=request)
            if not msg:
                return res, "error"
        return res, "ok"
    except Exception as error:
        write_exception(message=error, request=request)
        return error, "error"


def create_checklist(project_id, request):
    try:
        try:
            ProjectDescription.objects.create(project_id=project_id)
        except Exception as error:
            write_exception(error, request)

        file = open('data/checklist.json', 'r')
        data = json.loads(file.read())
        file.close()
        for index, checklist in enumerate(data['checklist']):
            TrainingCheckList.objects.create(
                task=checklist,
                position=index + 1,
                project_id=project_id
            )
    except Exception as error:
        write_exception(error, request)


def support_assignment_mail(support, request):
    try:
        project = support.project
        submission = project.submission
        consultant = project.submission.consultant

        project_start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
        poc_emails = list(consultant.pocs.filter(end=None).values_list('poc__email', flat=True))
        support_emails = list(project.support.all().values_list('support__email', flat=True))
        marketing_poc = list(User.objects.filter(
            team=submission.marketing_team, role__name='admin'
        ).values_list('email', flat=True))

        mail_data = {
            'template': '../templates/support_assignment.html',
            'to': [submission.created_by.email] + support_emails,
            'cc': ['engineering@consultadd.com'] + poc_emails + marketing_poc, 'bcc': [],
            'subject': f"{consultant.name}'s support initiated for  {project.submission.client} by"
                       f" {support.support.employee_name}",
            'context': {
                'support_name': support.support.employee_name,
                'client': submission.client, 'support_email': support.support.email,
                'consultant_name': consultant.name, 'consultant_email': consultant.email,
                'marketer_name': submission.created_by.employee_name, 'start': project_start_date,
                'job_title': submission.lead.job_title, 'consultant_phone_no': consultant.phone_no,
                'project_location': submission.lead.city, 'consultant_location': consultant.current_city,
            }
        }
        res, msg, _ = send_email(mail_data, request.user.email, request=request)
        if not msg:
            return res, "error"
        return res, "ok"
    except Exception as error:
        write_exception(message=error)
        return error, "error"


def check_days(start, end, request=None):
    try:
        days = 0
        while end >= start:
            if start.weekday() < 5:
                days += 1
            start = start + timedelta(days=1)
        return days
    except Exception as error:
        write_exception(message=error, request=request)
        return error, "error"


def send_employer_change_notification(project, data, request):
    try:
        project.submission.employer = project.employer
        project.submission.save()
        client = project.submission.client
        marketer_email = request.user.email
        consultant = project.submission.consultant.name
        mail_data = {
            'bcc': [],
            'cc': [config.SUPERADMIN],
            'to': [config.FINANCE, config.RELATIONS, "marketing@consultadd.com"],
            'template': "../templates/update_employer.html",
            'context': {
                'submission_id': project.submission.id, 'client': client,
                'consultant_name': consultant, 'prev_employer': data['prev_employer'],
                'new_employer': data['new_employer'], 'marketer_name': project.marketer_name,
            },
            'subject': f"Employer is updated for project {consultant} :: {client}"
        }
        desc = f"Employer changed from  {data['prev_employer']} to {data['new_employer']}"
        create_activity(project.submission.id, 'submission', request.user, desc, 'updated')
        mail(mail_data, marketer_email, request=request)
    except Exception as error:
        write_exception(message=error, request=request)
        return error, "error"


def mark_in_active():
    try:
        tz = timezone('EST')
        time_est = datetime.now(tz).replace(tzinfo=timezone('UTC'))
        events = TimetrackEvent.objects.filter(is_active=True, end__lt=time_est)
        for event in events:
            event.is_active = False
            event.save()
    except Exception as error:
        write_exception(message=error)
        return None


def timesheet_submission_mail(obj, request=None):
    try:
        project_type = "Timesheet" if obj.project.submission.work_type == 'c2c' else "Paystubs"
        if os.environ.get('ENV') == 'PROD':
            app_link = f"https://app.log1.com/#/finance/timesheet_details/{request.user.id}/{obj.project.id}"
        else:
            app_link = f"https://d2us7jrqrv1djj.cloudfront.net/#/finance/timesheet_details/{request.user.id}/{obj.project.id}"

        mail_data = {
            'cc': [], 'bcc': ['shreyas.k@consultadd.com'],
            'template': '../templates/timesheet_submission.html',
            'to': ['finance@consultadd.com'],
            'subject': f"{project_type} submission Info",
            'context': {
                'type': project_type,
                'client_name': obj.project.submission.client,
                'consultant_name': obj.project.consultant.name,
                'timesheet_date': f'{obj.start.strftime("%b %d, %Y")} - {obj.end.strftime("%b %d, %Y")}',
                'app_link': app_link
            }
        }
        send_email(mail_data, 'product@consultadd.com', request=request)
    except Exception as error:
        write_exception(error, request)
        return None
