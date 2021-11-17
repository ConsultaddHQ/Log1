from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from employee.models import User
from marketing.models import Interview
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    # A command must define handle()
    def handle(self, *args, **options):
        job = create_cron_object(name='teams_bot')
        try:
            text = f""" <tr>
                            <th style="padding:5px 8px 5px 8px;">#</th>
                            <th style="padding:5px 8px 5px 8px;">Marketer Name</th>
                            <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>"""
            marketers = User.objects.filter(
                is_active=True, role__name='marketer', team__dept="Marketing"
            ).order_by('team__name')
            count = 0
            for user in marketers:
                interview_count = Interview.objects.filter(submission__created_by=user, status='feedback_due').count()
                if interview_count != 0:
                    count = count+1
                    text += f"""<tr>
                                    <td style="padding:5px 8px 5px 8px;">{count}</td>
                                    <td style="padding:5px 8px 5px 8px;">{user.employee_name}</td>
                                    <td style="text-align: center;padding:5px 8px 5px 8px;">{interview_count}</td>
                                <tr>\n"""
            data = {
                "title": "Interviews count for feedback due status",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            res, msg = post_msg_using_webhook(config.announcement_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
