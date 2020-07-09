from django.core.management import BaseCommand
from constance import config
from marketing.models import Test
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # A command must define handle()
    def handle(self, *args, **options):
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

        engineering_channel_webhook = "https://outlook.office.com/webhook/ffe50b6c-3c3c-49d3-b2f5-c8076709b2ef@2646e092-48b1-46c2-aea1-02db36a98d68/IncomingWebhook/28dab3151e154652ae5a3183863a7f1f/825d0fa5-b150-4086-9abe-f47e87f878da"
        post_msg_using_webhook(engineering_channel_webhook, data)
