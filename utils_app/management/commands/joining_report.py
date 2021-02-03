from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from log1.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        month = date.today().month
        year = date.today().year
        if month == 1:
            last_month = 12
            last_year = year - 1
        else:
            last_year = year
            last_month = month - 1

        joined_last_month = Project.objects.filter(
            statuses__status__iexact='joined', statuses__created__year=last_year, statuses__created__month=last_month
        ).order_by('id').distinct('id').count()

        joined_this_month_t = Project.objects.filter(
            start_date__year=year, start_date__month=month, statuses__status__iexact='joined',
            statuses__created__year=year, statuses__created__month=month
        ).order_by('id').distinct('id').count()

        joined_this_month = Project.objects.filter(
            start_date__year=year, start_date__month=month, statuses__is_current=True,
            statuses__status__iexact='joined', statuses__created__year=year, statuses__created__month=month
        ).order_by('id').distinct('id').count()

        expected_joining = Project.objects.filter(
            start_date__year=year, start_date__day__gte=date.today().day, start_date__month=month
        ).count()

        offers_not_joined = Project.objects.filter(
            start_date__lt=date.today(),
            statuses__is_current=True,
            statuses__status__in=['new', 'received', 'on_boarded']
        ).count()

        data = {
            "title": "Projects joining status &#128221;",
            "text": f"""<table border='2' style='border-collapse:collapse'>
                            <tr>
                                <th style="padding:5px 8px 5px 8px;">Project Status</th>
                                <th style="padding:5px 8px 5px 8px;">Count</th>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Joined Last Month</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{joined_last_month}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Joined This Month</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{joined_this_month_t}/{joined_this_month}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Expected Joining this Month</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{expected_joining}</td>
                            </tr>
                            <tr>
                                <td style="padding:5px 8px 5px 8px;">Joining Status Not Updated in Log1</td>
                                <td style="text-align: center;padding:5px 8px 5px 8px;">{offers_not_joined}</td>
                            </tr>
                        </table>"""
        }
        post_msg_using_webhook(config.joined_url, data)
