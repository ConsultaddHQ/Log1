from datetime import date, timedelta, datetime
from django.core.management import BaseCommand

from constance import config
from employee.models import User
from utils_app.models import CronJob
from marketing.models import Submission
from log1.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        job = CronJob.objects.get(name='make_consultant_open')
        job.last_triggered_at = datetime.now()
        try:
            start = date.today() - timedelta(days=7)
            end = date.today() - timedelta(days=1)

            text = '<tr>' \
                   '<th style="padding:5px 8px 5px 8px;">Marketer</th>' \
                   '<th style="padding:5px 8px 5px 8px;">Team</th>' \
                   '<th style="padding:5px 8px 5px 8px;">Submission Count</th>' \
                   '</tr>'
            marketers = User.objects.filter(
                is_active=True, role__name='marketer', team__dept="Marketing"
            ).order_by('team__name')
            total = marketers.count()
            first, last = 0, 50
            while True:
                for user in marketers[first:last]:
                    submissions_count = Submission.objects.filter(created__range=[start, end], created_by=user,
                                                                  is_complete=True).count()
                    if submissions_count <= 5:
                        text += f"""<tr>
                                        <td style="padding:5px 8px 5px 8px;">{user.employee_name}</td>
                                        <td style="padding:5px 8px 5px 8px;">{user.team.name}</td>
                                        <td style="text-align: center;padding:5px 8px 5px 8px;">{submissions_count}</td>
                                    <tr>\n"""

                data = {
                    "title": "Submission Count &#128221;",
                    "text": f"""Date range - {start.strftime('%m/%d/%Y')} - {end.strftime('%m/%d/%Y')}<br>
                            <table border='2' style='border-collapse:collapse'>{text}</table>"""
                }

                post_msg_using_webhook(config.marketing_report_url, data)
                text = '<tr>' \
                       '<th style="padding:5px 8px 5px 8px;">Marketer</th>' \
                       '<th style="padding:5px 8px 5px 8px;">Team</th>' \
                       '<th style="padding:5px 8px 5px 8px;">Submission Count</th>' \
                       '</tr>'

                total -= 50
                if total > 0:
                    first = last
                    last = first + 50
                else:
                    break
            job.last_status = 'complete'
        except Exception as error:
            job.last_status = 'failed'
            print(error)

        finally:
            job.save()
