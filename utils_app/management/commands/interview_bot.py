from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Interview
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        from pytz import timezone
        tz = timezone('EST')
        today_date = tz.localize(datetime.now())
        interviews = Interview.objects.filter(
            start_time__date=today_date,
            status__in=['scheduled', 'rescheduled', 'feedback_due'],
            screening_type__in=['telephonic', 'video_call', 'skype', 'webex'],
        ).order_by('start_time')

        text = f""" #### Interviews Scheduled for today :clipboard:\n
| CTB | round | Type   | Start Time | Consultant | Client | Marketer |
|:----|:------|:-------|:-----------|:-----------|:-------|:---------|
"""
        for interview in interviews:
            text += f"""| {interview.supervisor.employee_name} | {interview.round} | {interview.get_screening_type_display()} | {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} | {interview.consultant} | {interview.submission.client} | {interview.marketer} |\n"""

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        post_msg_using_webhook(config.announcement_url, data)
