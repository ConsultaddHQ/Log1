from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from employee.models import Team
from project.models import Project
from marketing.models import Submission
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        teams = Team.objects.filter(dept='Marketing').order_by('name')
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=3)

        cancelled = ["cancel-dual-offer", "cancel-client-cancelled", "contract-conflicts", "candidate-absconded",
                     "candidate-denied-jd", "candidate-denied-rate", "candidate-denied-location"]
        text = f"""
#### Project Details :memo: \n
| Team | Submissions | Interviews | Offers | Joined | Cancelled | Completed | PO Received | Offer Not Joined |
|:-----|:------------|:-----------|:-------|:-------|:----------|:----------|:------------|:-----------------|
"""
        for team in teams:
            submissions = Submission.objects.filter(
                created_by__team=team, created__range=[start, end]
            ).exclude(status='draft')

            projects = Project.objects.filter(statuses__created__range=[start, end])

            submission_count = submissions.count()

            interview_count = submissions.filter(status__in=['interview', 'project']).count()

            offer_count = Project.objects.filter(
                created__range=[start, end], submission__created_by__team=team
            ).count()

            joined_count = projects.filter(statuses__status__iexact='joined').count()

            cancelled_count = projects.filter(statuses__status__in=cancelled).count()

            completed_count = projects.filter(statuses__status__iexact='completed').count()

            on_roll_count = projects.filter(statuses__status__in=['received', 'on_boarded']).count()

            offers_not_joined = Project.objects.filter(
                start_date__lt=date.today(), submission__created_by__team=team
            ).exclude(statuses__is_current=True, statuses__status__iexact='joined').count()

            text += f"| {team.name.title()} | {submission_count} | {interview_count} | {offer_count} | {joined_count} | {cancelled_count} | {completed_count} | {on_roll_count} | {offers_not_joined} |\n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        mattermost_webhook(config.offer_url, data)
