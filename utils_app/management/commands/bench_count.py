from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.slack_notification import MessageCard
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Consultant's Bench count"

    def handle(self, *args, **options):
        job = create_cron_object(name='bench_count')
        try:
            queryset = Consultant.objects.filter(marketing__status='open').exclude(status='terminated').distinct()
            on_bench_con = queryset.count()
            in_pool_con = queryset.filter(marketing__in_pool=True).count()
            on_boarded = Consultant.objects.filter(
                projects__statuses__status='on_boarded',
                projects__statuses__is_current=True
            ).exclude(status='terminated').distinct().count()
            joined = Consultant.objects.filter(
                projects__statuses__status='on_boarded',
                projects__statuses__is_current=True
            ).exclude(status='terminated').distinct().count()

            data = {
                "title": "Consultant Bench Status &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Status</th>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Bench</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em; text-align: center;">{on_bench_con}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">In Pool</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em; text-align: center;">{in_pool_con}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> On Boarded </td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em; text-align: center;">{on_boarded}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Joined</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em; text-align: center;">{joined}</td>
                                </tr>
                            </table>"""
            }

            payload = {
                "data": data, "report_name": "consultant_bench",
                "title": f"{data.get('title')} :MEMO:",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_recruitment_url)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
