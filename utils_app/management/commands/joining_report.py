from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.slack_notification import MessageCard
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Project joining Status"

    def handle(self, *args, **options):
        job = create_cron_object(name='joining_report')
        try:
            month = date.today().month
            year = date.today().year
            if month == 1:
                last_month = 12
                last_year = year - 1
            else:
                last_year = year
                last_month = month - 1

            joined_last_month = Project.objects.filter(
                statuses__status__iexact='joined', statuses__created__year=last_year,
                statuses__created__month=last_month
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
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>
            <tr>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Project Status</th>
                <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
            </tr>
            <tr>
                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Joined Last Month</td>
                <td style="text-align: center;padding:5px 8px 5px 8px;">{joined_last_month}</td>
            </tr>
            <tr>
                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Joined This Month</td>
                <td style="text-align: center;padding:5px 8px 5px 8px;">{joined_this_month_t}/{joined_this_month}</td>
            </tr>
            <tr>
                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Expected Joining this Month</td>
                <td style="text-align: center;padding:5px 8px 5px 8px;">{expected_joining}</td>
            </tr>
            <tr>
                <td style="padding:5px 8px 5px 8px;font-size: 2.5em;">Joining Status Not Updated in Log1</td>
                <td style="text-align: center;padding:5px 8px 5px 8px;">{offers_not_joined}</td>
            </tr>
                            </table>"""
            }
            payload = {
                "data": data, "report_name": "project_joining",
                "title": data.get('title'),
            }
            # res, msg = MessageCard.data_report(payload, config.slack_usa_joining_termination)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
