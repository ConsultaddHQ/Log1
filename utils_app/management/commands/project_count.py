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
        month = date.today().month
        new_offer = Project.objects.filter(statuses__status='new', statuses__is_current=True).count()
        received_projects = Project.objects.filter(statuses__status='received', statuses__is_current=True).count()
        on_boarded_projects = Project.objects.filter(statuses__status='on_boarded', statuses__is_current=True).count()
        joined_projects = Project.objects.filter(statuses__status='joined', statuses__is_current=True,
                                                 created__month=month).count()
        cancelled_projects = Project.objects.filter(statuses__status__in=cancelled, statuses__is_current=True,
                                                    created__month=month).count()
        terminated_projects = Project.objects.filter(statuses__status__in=terminated, statuses__is_current=True,
                                                     created__month=month).count()
        total_projects = Project.objects.filter(statuses__created__month=month, statuses__is_current=True).exclude(
            statuses__status__in=['new']).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Project Details :memo: \n
| Project Status     | Count   | 
|:--------------------|:-----------|
| New Offer | {new_offer} |
| Paper Work Received | {received_projects} |
| On boarded | {on_boarded_projects} |
"""
        }
        mattermost_webhook(config.offer_url, data)

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Business Health for this month :memo: \n
| Project Status    |  Count  | 
|:--------------------|:-----------|
| Joined  | {joined_projects} |
| Cancelled   | {cancelled_projects} |
| Terminated   | {terminated_projects} |
| Total Offer  | {total_projects} |
"""
        }
        mattermost_webhook(config.offer_url, data)
