from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from employee.models import Team
from project.models import Project
from marketing.models import Submission, Interview
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        teams = Team.objects.filter(dept='Marketing').order_by('name')
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=1)

        joined_or_terminated = ["resigned-rate", "resigned-location", "resigned-full_time", "resigned-technology",
                                "client-fired-budget", "client-fired-performance", "client-fired-security", "joined",
                                "completed"]

        cancelled = ["cancel-dual-offer", "cancel-client-cancelled", "contract-conflicts", "candidate-absconded",
                     "candidate-denied-jd", "candidate-denied-rate", "candidate-denied-location"]

        text = f"""
#### Project Details :memo: \n
| Team | Submissions | Interviews | Offers | Joined | Cancelled | Completed | PO Received | Offer Not Joined |
|:-----|:------------|:-----------|:-------|:-------|:----------|:----------|:------------|:-----------------|
"""
        total_submission, total_interview, total_joined, total_cancelled = 0, 0, 0, 0
        total_complete, total_on_roll, total_offer_not_joined, total_offer = 0, 0, 0, 0

        projects = Project.objects.filter(statuses__created__range=[start, end])
        for team in teams:
            submission_count = Submission.objects.filter(
                created_by__team=team, created__range=[start, end]
            ).exclude(status='draft').count()
            total_submission += submission_count

            interview_count = Interview.objects.filter(
                submission__created_by__team=team,
                created__range=[start, end]
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            total_interview += interview_count

            offer_count = projects.filter(created__range=[start, end], submission__created_by__team=team).count()
            total_offer += offer_count

            joined_count = projects.filter(
                statuses__status__iexact='joined', statuses__is_current=True, submission__created_by__team=team
            ).count()
            total_joined += joined_count

            cancelled_count = projects.filter(
                statuses__status__in=cancelled, statuses__is_current=True, submission__created_by__team=team
            ).count()
            total_cancelled += cancelled_count

            completed_count = projects.filter(
                statuses__status__iexact='completed', statuses__is_current=True, submission__created_by__team=team
            ).count()
            total_complete += completed_count

            on_roll_count = projects.filter(
                statuses__is_current=True,
                submission__created_by__team=team,
                statuses__status__in=['received', 'on_boarded'],
            ).count()
            total_on_roll += on_roll_count

            offers_not_joined = Project.objects.filter(
                start_date__range=[start, end], submission__created_by__team=team
            ).exclude(statuses__is_current=True, statuses__status__in=joined_or_terminated).count()
            total_offer_not_joined += offers_not_joined

            text += f"| {team.name.title()} | {submission_count} | {interview_count} | {offer_count} | {joined_count} | {cancelled_count} | {completed_count} | {on_roll_count} | {offers_not_joined} |\n"

        text += f"| Total | {total_submission} | {total_interview} | {total_offer} | {total_joined} | {total_cancelled} | {total_complete} | {total_on_roll} | {total_offer_not_joined} |\n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        mattermost_webhook(config.marketing_report_url, data)
