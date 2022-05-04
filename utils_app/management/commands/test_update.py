from django.core.management import BaseCommand

from constance import config
from marketing.models import Test
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for sending Test status count report on channel"

    def handle(self, *args, **options):
        job = create_cron_object(name='test_update')
        try:
            new = Test.objects.filter(status__iexact='new').count()
            feedback_due = Test.objects.filter(status__iexact='feedback_due').count()
            passed = Test.objects.filter(status__iexact='passed').count()
            failed = Test.objects.filter(status__iexact='failed').count()
            total = new + feedback_due + passed + failed
            data = {
                "title": "Test/Assignment Status &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;">Status</th>
                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">New</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{new}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Feedback Due</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{feedback_due}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Passed</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{passed}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Failed</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{failed}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Total</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{total}</td>
                                </tr>
                            </table>"""
            }

            res, msg = post_msg_using_webhook(config.engineering_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
