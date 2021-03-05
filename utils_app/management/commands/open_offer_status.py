from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()

    def handle(self, *args, **options):
        job = CronJob.objects.get(name='open_offer_status')
        job.last_triggered_at = datetime.now()
        job.save()
        try:
            new = Project.objects.filter(
                statuses__is_current=True, statuses__status__iexact='new'
            ).count()

            received = Project.objects.filter(
                statuses__is_current=True, statuses__status__iexact='received',
            ).count()

            on_boarded = Project.objects.filter(
                statuses__is_current=True, statuses__status__iexact='on_boarded',
            ).count()

            total = new + received + on_boarded

            data = {
                "title": "Open Offer Status &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;">PO Status</th>
                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">New</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{new}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Received</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{received}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">On-boarded</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{on_boarded}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Total</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{total}</td>
                                </tr>
                            </table>"""
            }
            res, msg = post_msg_using_webhook(config.marketing_report_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
