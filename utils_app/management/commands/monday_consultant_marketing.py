from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Consultants moved to Marketing"

    def handle(self, *args, **options):
        job = create_cron_object(name='monday_consultant_marketing')
        try:
            end = date.today() - timedelta(days=1)
            start = date.today() - timedelta(days=7)

            queryset = Consultant.objects.filter(marketing__status='open').exclude(status='terminated').distinct()
            total = queryset.count()
            dev = queryset.filter(marketing__status='open', marketing__start__range=[start, end], domain='dev').count()
            ba = queryset.filter(marketing__status='open', marketing__start__range=[start, end],
                                 domain='analyst').count()

            data = {
                "title": "Consultant Moved to Marketing &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Status</th>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Dev</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{dev}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">BA</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{ba}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Total</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{total}</td>
                                </tr>
                            </table>"""
            }
            payload = {
                "data": data, "title": data.get('title'),
                "report_name": "consultant_moved_marketing",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_recruitment_url)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
