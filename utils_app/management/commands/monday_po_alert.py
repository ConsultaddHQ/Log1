from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.views import mattermost_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=3)

        projects = Project.objects.filter(
            statuses__status__iexact='joined', statuses__is_current=True,
        )

        joined_last_week = projects.filter(
            statuses__created__range=[start, end]
        ).count()

        start = date.today()
        end = date.today() + timedelta(days=4)

        joining_this_week = projects.filter(
            statuses__created__range=[start, end]
        ).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Open Offer Status :memo: \n
| PO Status   |    Count   | 
|:------------|:-----------|
| Joined Last Week | {joined_last_week} |
| Joining in this Week | {joining_this_week} |
"""
        }
        mattermost_webhook(config.offer_url, data)
