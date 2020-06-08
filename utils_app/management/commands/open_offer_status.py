from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()

    def handle(self, *args, **options):
        new = Project.objects.filter(
            statuses__is_current=True, statuses__status__iexact='new'
        ).count()

        received = Project.objects.filter(
            statuses__is_current=True, statuses__status__iexact='received',
        ).count()

        on_boarded = Project.objects.filter(
            statuses__is_current=True, statuses__status__iexact='on_boarded',
        ).count()

        total = new + received + on_boarded

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Open Offer Status :memo: \n
| PO Status  |     Count    | 
|:-----------|:-------------|
| new        |    {new}     |
| Received   |  {received}  |
| On-boarded | {on_boarded} |
| Total      |   {total}    |
"""
        }
        post_msg_using_webhook(config.marketing_report_url, data)
