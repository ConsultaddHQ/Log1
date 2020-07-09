from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Test
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    def handle(self, *args, **options):
        tests = Test.objects.filter(status='new').order_by('created')

        text = f""" <tr>
            <th style="padding:5px 8px 5px 8px;">Created</th>
            <th style="padding:5px 8px 5px 8px;">Marketer</th>
            <th style="padding:5px 8px 5px 8px;">Consultant</th>
            <th style="padding:5px 8px 5px 8px;">Skills</th>
            <th style="padding:5px 8px 5px 8px;">Client</th>
            <th style="padding:5px 8px 5px 8px;">Video</th>
            <th style="padding:5px 8px 5px 8px;">Deadline</th>
            </tr>"""

        for test in tests:
            skills = ", ".join(skill for skill in test.skills)
            deadline = 'NA'
            if test.deadline:
                deadline = test.deadline.strftime('%m/%d/%Y')
            text += f"""<tr>
                            <td style="padding:5px 8px 5px 8px;"> {test.created.strftime('%a, %d %B')} </td>
                            <td style="padding:5px 8px 5px 8px;"> {test.submission.created_by.employee_name} </td>
                            <td style="padding:5px 8px 5px 8px;"> {test.submission.consultant.name} </td>
                            <td style="padding:5px 8px 5px 8px;"> {skills} </td>
                            <td style="padding:5px 8px 5px 8px;"> {test.submission.client} </td>
                            <td style="padding:5px 8px 5px 8px;"> {"Yes" if test.is_video else "No"} </td>
                            <td style="padding:5px 8px 5px 8px;"> {datetime.strptime(deadline, '%m/%d/%Y').strftime('%a, %d %B')} </td>
                        </tr>"""
        data = {
            "title": "Pending Test &#128203;",
            "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
        }

        test_channel_webhook = "https://outlook.office.com/webhook/2b6b8987-33b0-4a36-bb5e-bd9b94bb2b12@2646e092-48b1-46c2-aea1-02db36a98d68/IncomingWebhook/d791a6acc44441fd9194e04a1f6aa311/825d0fa5-b150-4086-9abe-f47e87f878da"
        post_msg_using_webhook(test_channel_webhook, data)
