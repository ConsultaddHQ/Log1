from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        end = date.today() - timedelta(days=1)
        start = date.today() - timedelta(days=7)

        text = f"""
#### Project Joined Last Week :memo: \n
| Consultant | Team | Client | Vendor | Marketer | Start Date | Employer | City |
|:-----------|:-----|:-------|:-------|:---------|:-----------|:---------|:-----|
"""

        joined_last_week = Project.objects.filter(
            statuses__status__iexact='joined',
            start_date__range=[start, end],
            statuses__is_current=True,
        )
        for project in joined_last_week:
            submission = project.submission
            text += f"| {project.consultant.name} | {submission.created_by.team.name} | {submission.client} | {submission.lead.vendor_company.name} | {submission.created_by.employee_name} | {project.start_date} | {submission.employer} | {project.city} |\n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        mattermost_webhook(config.joined_url, data)

        text = f"""
#### Project Joining in this Week :memo: \n
| Consultant | Team | Client | Vendor | Marketer | Start Date | Employer | City |
|:-----------|:-----|:-------|:-------|:---------|:-----------|:---------|:-----|
"""
        start = date.today()
        end = date.today() + timedelta(days=5)
        cancelled = ["cancel-dual-offer", "cancel-client-cancelled", "contract-conflicts", "candidate-absconded",
                     "candidate-denied-jd", "candidate-denied-rate", "candidate-denied-location"]

        joining_this_week = Project.objects.filter(start_date__range=[start, end]).exclude(
            statuses__status__in=cancelled,
            statuses__is_current=True,
        )

        for project in joining_this_week:
            submission = project.submission
            text += f"| {project.consultant.name} | {submission.created_by.team.name} | {submission.client} | {submission.lead.vendor_company.name} | {submission.created_by.employee_name} | {project.start_date} | {submission.employer} | {project.city} |\n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        mattermost_webhook(config.joined_url, data)
        mattermost_webhook(config.general_url, data)
