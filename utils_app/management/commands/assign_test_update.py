from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Test
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_test_update')
        try:
            tests = Test.objects.filter(status__in=['new', 'assigned']).exclude(
                submission__consultant_marketing__status='close'
            ).order_by('-modified')

            text = f""" <tr>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">#</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Created</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Marketer</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Consultant</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Assigned to</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Client</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Video</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Deadline</th>
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
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {index + 1} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {test.created.strftime('%a, %d %B')} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {test.submission.created_by.employee_name} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {test.submission.consultant.name} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {assigned_to} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {test.submission.client} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {"Yes" if test.is_video else "No"} </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {deadline} </td>
                                </tr>"""
                data = {
                    "title": "New/Assigned Test &#128203;",
                    "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
                }
            else:
                data = {
                    "title": "New/Assigned Test &#128203;",
                    "text": "No Pending test"
                }

            payload = {
                "data": data, "report_name": "new/assigned_test",
                "title": f"{data.get('title')} :MEMO:",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_engineering_url)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
