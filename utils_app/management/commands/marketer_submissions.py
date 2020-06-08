from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from employee.models import User
from marketing.models import Submission
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=1)

        text = f"""
#### Submission Count :memo: \n
Date range - {start} - {end} \n
| Marketer | Team | Submission Count |
|:---------|:-----|:-----------------|
"""
        marketers = User.objects.filter(is_active=True, role__name='marketer', team__dept="Marketing").order_by('team__name')
        submissions = Submission.objects.filter(created__range=[start, end])
        for user in marketers:
            submissions_count = submissions.filter(created_by=user).count()
            if submissions_count <= 5:
                text += f"| {user.employee_name} | {user.team.name} | {submissions_count} |\n"

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        post_msg_using_webhook(config.marketing_report_url, data)
