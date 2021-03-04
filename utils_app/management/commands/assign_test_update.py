from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Test
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook, create_cron_error


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = CronJob.objects.get(name='assign_test_update')
        job.last_triggered_at = datetime.now()
        job.save()
        try:
            tests = Test.objects.filter(status__in=['new', 'assigned']).exclude(
                submission__consultant_marketing__status='close'
            ).order_by('-modified')

            text = f""" <tr>
                <th style="padding:5px 8px 5px 8px;">#</th>
                <th style="padding:5px 8px 5px 8px;">Created</th>
                <th style="padding:5px 8px 5px 8px;">Marketer</th>
                <th style="padding:5px 8px 5px 8px;">Consultant</th>
                <th style="padding:5px 8px 5px 8px;">Assigned to</th>
                <th style="padding:5px 8px 5px 8px;">Client</th>
                <th style="padding:5px 8px 5px 8px;">Video</th>
                <th style="padding:5px 8px 5px 8px;">Deadline</th>
                </tr>"""
            if tests.count() > 0:
                for index, test in enumerate(tests):
                    assigned_to = 'Not Assigned'
                    assigned = test.assign_to.all()
                    if test.deadline:
                        deadline = datetime.strptime(str(test.deadline), '%Y-%m-%d').strftime('%a, %d %B')
                    else:
                        deadline = 'NA'
                    if assigned.count() > 0:
                        assigned_to = ", ".join(assign.employee_name for assign in assigned)
                    text += f"""<tr>
                                    <td style="padding:5px 8px 5px 8px;"> {index + 1} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {test.created.strftime('%a, %d %B')} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {test.submission.created_by.employee_name} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {test.submission.consultant.name} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {assigned_to} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {test.submission.client} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {"Yes" if test.is_video else "No"} </td>
                                    <td style="padding:5px 8px 5px 8px;"> {deadline} </td>
                                </tr>"""
                data = {
                    "title": "New/Assigned Test &#128203;",
                    "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
                }
            else:
                data = {
                    "title": "New/Assigned Test &#128203;",
                    "text": "No Pending test"
                }

            res, msg = post_msg_using_webhook(config.engineering_url, data)
            if msg == 'error':
                create_cron_error(job, res)
        except Exception as error:
            create_cron_error(job, error)
