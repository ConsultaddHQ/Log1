from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404

from constance import config
from employee.models import User
from consultant.models import Consultant
from project.models import Project, TimeSheet
from consultant.utils import send_notification_for_user
from log1.utils import Http400, post_msg_using_webhook, password_generator


def set_consultant_password(consultant):
    if not consultant.is_active:
        password = password_generator(password_length=10, strength=3)
        consultant.set_password(password)
        consultant.is_active = True
        consultant.save()
        return password, True
    return "password", False


# Creating consultant object from user for remote
def create_remote_consultant(request):
    remote_consultant_id = request.data.get('remote_consultant_id', None)
    consultant = None
    if remote_consultant_id:
        if request.data.get("remote_consultant_type", None) == 'user':
            user = get_object_or_404(User, id=remote_consultant_id)
            consultant, _ = Consultant.objects.get_or_create(email=user.email)
            consultant.remote_only = True
            consultant.gender = user.gender
            consultant.name = user.employee_name
            consultant.save()
        else:
            consultant = get_object_or_404(Consultant, id=remote_consultant_id)

    return consultant


class ProjectUtil:
    def __init__(self, project):
        self.project = project
        self.project_end = None
        self.statuses = self.fetch_project_status()
        self.project_start = datetime.strptime(str(project.start_date), '%Y-%m-%d').strftime('%m/%d/%Y')
        if project.end_date:
            self.project_end = datetime.strptime(str(project.end_date), '%Y-%m-%d').strftime('%m/%d/%Y')

    @staticmethod
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

    def fetch_emojis(self):
        try:
            # Emojis of messaging app
            emoji = {}
            recruiter = self.project.consultant.recruiter
            if recruiter:
                emoji['recruiter_gender'] = '&#128103;' if recruiter.gender == 'female' else '&#129490;'
                emoji['recruiter_name'] = recruiter.employee_name
            else:
                emoji['recruiter_gender'] = '&#129490; '
                emoji['recruiter_name'] = "NA"

            emoji['role'] = '&#128074;'
            emoji['client'] = '&#127913;'
            emoji['employer'] = '&#x1F4BC;'
            emoji['consultant_gender'] = '&#128105;' if self.project.consultant.gender == 'female' else '&#128104;'
            emoji['marketer_gender'] = '&#128105;' if self.project.submission.created_by.gender == 'female' else '&#128104;'

            return emoji
        except Exception as error:
            raise Http400(str(error))

    def fetch_project_count(self, project_status, emoji):
        day_one = datetime.today().replace(day=1, hour=0, minute=0)
        total_count = Project.objects.filter(
            statuses__status=project_status,
            statuses__created__gte=day_one,
        ).count()

        team_count = Project.objects.filter(
            statuses__status=project_status,
            statuses__created__gte=day_one,
            employer__iexact=self.project.employer,
        ).count()

        if self.project.is_remote or self.project.submission.lead.is_w2:
            con_str = f"**Remote Project** <br>"
            con_str += f"{emoji} Consultant Joined: **{self.project.consultant.name.strip()}** <br>"
            con_str += f"{emoji} Submitted On: **{self.project.consultant.name.strip()}** "
        else:
            con_str = f"{emoji} Consultant :  **{self.project.consultant.name.strip()}** "

        return total_count, team_count, con_str

    def send_join_notification(self, user):
        # Emoji for Message
        emojis = self.fetch_emojis()
        total, team, con_str = self.fetch_project_count("joined", emojis['consultant_gender'])

        data = {
            "title": "Project Joined  &#129304;&#128516;&#129304;",
            "text": f"""{con_str}<br>
            {emojis['marketer_gender']} Marketer :  {self.project.marketer_name} <br>
            {emojis['recruiter_gender']} Recruiter :  {emojis['recruiter_name']} <br>
            {emojis['employer']} Employer :  {self.project.employer}<br>
            {emojis['employer']} Team :  {self.project.submission.created_by.team.name}<br>
            🇺🇸 Location :  {self.project.city}<br>
            {emojis['client']} Client :  {self.project.submission.client}<br>
            {emojis['role']} Role :  {self.project.submission.lead.job_title}<br>
            &#128221; Joining Date :  {self.project_start}<br><br>
            Project Joined count of {self.project.employer} for this month - {team}<br>
            Total Project Joined count of this month - {total}"""
        }
        # Sending message on Messaging Tool
        post_msg_using_webhook(config.joined_url, data)

        title = f" Project Joined :: {self.project.consultant.name} :: {self.project.submission.client}"
        send_notification_for_user(self.project.consultant, user, title, 'project')

    def send_receive_notification(self, user):
        # Emoji for Message
        emojis = self.fetch_emojis()
        total, team, con_str = self.fetch_project_count("received", emojis['consultant_gender'])

        interviews = self.project.submission.screening.exclude(status='cancelled')
        ctb_gender = interviews.last().supervisor.gender
        supervisors = "\n".join(
            [f"<li>Round {interview.round} - {interview.supervisor.employee_name}</li>"
             for interview in interviews if interview.supervisor])
        ctb_gender_emoji = '&#128587;' if ctb_gender == 'female' else '&#129490;'

        data = {
            "title": "Offer  &#129304;&#128516;&#129304;",
            "text": f"""{con_str} <br>
                {emojis['marketer_gender']} Marketer :  {self.project.marketer_name} <br>
                {emojis['recruiter_gender']} Recruiter :  {emojis['recruiter_name']} <br>
                {emojis['employer']} Employer :  {self.project.employer}<br>
                {emojis['employer']} Team :  {self.project.submission.created_by.team.name}<br>
                {ctb_gender_emoji} CTB :  <ul>{supervisors}</ul> 🇺🇸 Location :  {self.project.city}
                <br> {emojis['client']} Client :  {self.project.submission.client}
                <br> {emojis['role']} Role :  {self.project.submission.lead.job_title}
                <br> &#128221; Start Date :  {self.project_start}
                <br> <br> Offer count of {self.project.employer} for this month - {team}
                <br> Total offer count of this month - {total}"""
        }
        # Sending message on Messaging Tool
        post_msg_using_webhook(config.offer_url, data)

        title = f" Project Received :: {self.project.consultant.name} :: {self.project.submission.client}"
        send_notification_for_user(self.project.consultant, user, title, 'self.project')

    def send_termination_notification(self, po_status, user):
        # Emoji for Message
        emojis = self.fetch_emojis()

        text = f"""{emojis['consultant_gender']} Consultant :  **{self.project.consultant.name}** <br>
            {emojis['marketer_gender']} Marketer :  {self.project.marketer_name} <br>
            {emojis['recruiter_gender']} Recruiter :  {emojis['recruiter_name']} <br>
            {emojis['employer']} Employer :  {self.project.employer} <br>
            {emojis['employer']} Team :  {self.project.submission.created_by.team.name} <br>
            {emojis['client']} Client :  {self.project.submission.client} <br>
            {emojis['role']} Role :  {self.project.submission.lead.job_title} <br>
            &#128221; Start Date :  {self.project_start} <br>
            &#128221; End Date :  {self.project_end} <br>
            &#10060; Status :  {po_status} <br>"""

        data = {
            "title": "Offer Termination Feedback",
            "text": text + " **Reason:** " + " " + self.project.feedback if self.project.feedback else "None"
        }
        # Sending message on Messaging Tool
        post_msg_using_webhook(config.project_termination_url, data)

        title = f"Project Terminated :: {self.project.consultant.name} :: {self.project.submission.client}"
        send_notification_for_user(self.project.consultant, user, title, 'project')

    def send_cancellation_notification(self, user):
        # Emoji for Message
        emojis = self.fetch_emojis()

        text = f"""{emojis['consultant_gender']} Consultant :  **{self.project.consultant.name}** <br>
            {emojis['marketer_gender']} Marketer :  {self.project.marketer_name} <br>
            {emojis['recruiter_gender']} Recruiter :  {emojis['recruiter']} <br>
            {emojis['employer']} Employer :  {self.project.employer}<br>
            {emojis['employer']} Team :  {self.project.submission.created_by.team.name}<br>
             🇺🇸 Location :  {self.project.city}<br>
            {emojis['client']} Client :  {self.project.submission.client}<br>
            {emojis['role']} Role :  {self.project.submission.lead.job_title}<br>
            &#128221; Joining Date :  {self.project_start}<br>"""

        data = {
            "title": "Offer Cancellation Feedback ",
            "text": text + " **Reason:** " + self.project.feedback if self.project.feedback else "None"
        }
        # Sending message on Messaging Tool
        post_msg_using_webhook(config.offer_failure_url, data)

        title = f"Project Cancelled :: {self.project.consultant.name} :: {self.project.submission.client}"
        send_notification_for_user(self.project.consultant, user, title, 'self.project')

    def send_completion_notification(self, user):
        title = f" Project Completed :: {self.project.consultant.name} :: {self.project.submission.client}"
        send_notification_for_user(self.project.consultant, user, title, 'project')

    def create_timesheet(self):
        start_date = datetime.strptime(str(self.project.start_date), '%Y-%m-%d')
        week_day = start_date.weekday()
        if week_day == 6:
            end_date = start_date + timedelta(days=6)
        else:
            end_date = start_date + timedelta(days=5 - week_day)

        for i in range(2):
            TimeSheet.objects.get_or_create(
                hours=0,
                end=end_date,
                status='draft',
                project=self.project,
                start=start_date,
            )
            start_date = end_date + timedelta(days=1)
            end_date = end_date + timedelta(days=7)
