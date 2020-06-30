from django.core.management import BaseCommand

from datetime import date, timedelta
from constance import config
from consultant.models import Consultant
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        end = date.today() - timedelta(days=1)
        start = date.today() - timedelta(days=7)

        queryset = Consultant.objects.filter(marketing__status='open').exclude(status='archived').distinct()
        total = queryset.count()
        dev = queryset.filter(marketing__status='open', marketing__start__range=[start, end], domain='dev').count()
        ba = queryset.filter(marketing__status='open', marketing__start__range=[start, end], domain='analyst').count()

        data = {
            "title": "Consultant Moved to Marketing &#128221;",
            "text": f"""<table border='2' style='border-collapse:collapse'>
                            <tr>
                                <th style="padding:5px 8px 5px 8px;">Status</th>
                                <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Dev</td>
                                <td style="padding:5px 8px 5px 8px;text-align: center;">{dev}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">BA</td>
                                <td style="padding:5px 8px 5px 8px;text-align: center;">{ba}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Total</td>
                                <td style="padding:5px 8px 5px 8px;text-align: center;">{total}</td>
                            </tr>
                        </table>"""
        }
        post_msg_using_webhook(config.recruitment_url, data)
