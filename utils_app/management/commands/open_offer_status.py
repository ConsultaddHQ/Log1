from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()

    def handle(self, *args, **options):
        cancelled = ["cancel-dual-offer", "cancel-client-cancelled", "contract-conflicts", "candidate-absconded",
                     "candidate-denied-jd", "candidate-denied-rate", "candidate-denied-location"]
        terminated = ["completed", "resigned-rate", "resigned-location", "resigned-full_time", "resigned-technology",
                      "client-fired-budget", "client-fired-performance", "client-fired-security"]

        new_offer = Project.objects.filter(
            statuses__status='new', statuses__is_current=True
        ).count()

        received_projects = Project.objects.filter(
            statuses__is_current=True, statuses__status__in=['received', 'on_boarded'],
        ).count()

        joined_projects = Project.objects.filter(
            statuses__status='joined', statuses__is_current=True
        ).count()

        cancelled_terminated_projects = Project.objects.filter(
            statuses__is_current=True, statuses__status__in=cancelled + terminated,
        ).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Open Offer Status :memo: \n
| PO Status   |    Count   | 
|:------------|:-----------|
| new         | {new_offer} |
| Yet to Join | {received_projects} |
| Terminated  | {cancelled_terminated_projects} |
| Joined      | {joined_projects} |
"""
        }
        mattermost_webhook(config.offer_url, data)
