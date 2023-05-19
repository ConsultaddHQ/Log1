from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting open project offers"

    def handle(self, *args, **options):
        job = create_cron_object(name='open_offer_status')
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
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">PO Status</th>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">New</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{new}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Received</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{received}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">On-boarded</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{on_boarded}</td>
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
            # res, msg = MessageCard.data_report(payload, config.slack_marketing_report_url)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
