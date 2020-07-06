from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        queryset = Consultant.objects.filter(marketing__status='open').exclude(status='archived').distinct()
        on_bench_con = queryset.count()
        in_pool_con = queryset.filter(marketing__in_pool=True).count()
        on_boarded = Consultant.objects.filter(
            projects__statuses__status='on_boarded',
            projects__statuses__is_current=True
        ).exclude(status='archived').distinct().count()
        joined = Consultant.objects.filter(
            projects__statuses__status='on_boarded',
            projects__statuses__is_current=True
        ).exclude(status='archived').distinct().count()

        data = {
            "title": "Consultant Bench Status &#128221;",
            "text": f"""<table border='2' style='border-collapse:collapse'>
                            <tr>
                                <th style="padding:5px 8px 5px 8px;">Status</th>
                                <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Bench</td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;">{on_bench_con}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">In Pool</td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;">{in_pool_con}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;"> On Boarded </td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;">{on_boarded}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Joined</td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;">{joined}</td>
                            </tr>
                        </table>"""
        }

        post_msg_using_webhook(config.recruitment_url, data)
