from django.core.management import BaseCommand

from constance import config
from marketing.models import Test
from utils_app.slack_notification import MessageCard
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
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Status</th>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">New</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{new}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Feedback Due</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{feedback_due}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Passed</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{passed}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Failed</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{failed}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Total</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{total}</td>
                                </tr>
                            </table>"""
            }

            payload = {
                "data": data, "title": data.get('title'), "report_name": job.name,
            }
            # res, msg = MessageCard.data_report(payload, config.slack_engineering_url)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
