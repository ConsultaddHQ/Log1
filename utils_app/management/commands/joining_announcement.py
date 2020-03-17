from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        month = date.today().month
        year = date.today().year

        terminated = ["completed", "resigned-rate", "resigned-location", "resigned-full_time", "resigned-technology",
                      "client-fired-budget", "client-fired-performance", "client-fired-security"]

        projects = Project.objects.filter(
            statuses__created__year=year,
            statuses__created__month=month
        )

        joined_projects = projects.filter(
            statuses__is_current=True,
            statuses__status__iexact='joined',
        ).count()

        net_joined_project = projects.filter(
            statuses__status__iexact='joined',
        ).count() - projects.filter(
            statuses__is_current=True,
            statuses__status__in=terminated,
        ).count()

        total_projects = Project.objects.filter(
            created__year=year,
            created__month=month,
        ).exclude(statuses__status__in=['new']).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### PO joining status for this month :memo: \n
| Project Status |      Count            | 
|:---------------|:----------------------|
| Joined         |   {joined_projects}   |
| Net Joined     | {net_joined_project}  |
| Total Offer    |   {total_projects}    |
"""
        }
        mattermost_webhook(config.offer_url, data)
