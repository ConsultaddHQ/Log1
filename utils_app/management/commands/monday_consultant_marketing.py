from django.core.management import BaseCommand

from datetime import date, timedelta
from constance import config
from consultant.models import Consultant
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        end = date.today() - timedelta(days=1)
        start = date.today() - timedelta(days=7)

        queryset = Consultant.objects.filter(marketing__status='open').exclude(status='archived').distinct()
        total = queryset.count()
        dev = queryset.filter(marketing__status='open', marketing__start__range=[start, end], domain='dev').count()
        ba = queryset.filter(marketing__status='open', marketing__start__range=[start, end], domain='analyst').count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Consultant Moved to Marketing :memo: \n
| Status |  Count  |
|:-------|:--------|
|   Dev  |  {dev}  |
|   BA   |  {ba}   | 
|  Total | {total} |
"""
        }

        post_msg_using_webhook(config.recruitment_url, data)
