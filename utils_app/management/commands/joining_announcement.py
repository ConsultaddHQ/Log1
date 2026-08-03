from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.slack_notification import MessageCard
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Project joining"

    def handle(self, *args, **options):
        job = create_cron_object(name='joining_announcement')
        try:
            month = date.today().month
            year = date.today().year

            terminated = ['terminated', 'terminated-resigned', 'terminated-fired', 'terminated-resigned_rate_issue',
                          'terminated-resigned_technology_issue', 'terminated-fired_budget_issue',
                          'terminated-fired_security_issue', 'terminated-resigned_location_issue',
                          'terminated-fired_performance_issue', 'terminated-resigned_full_time_offer']

            projects = Project.objects.filter(
                created__year=year,
                created__month=month,
                statuses__created__year=year,
                statuses__created__month=month
            ).order_by('id').distinct('id')

            total_projects = projects.count()

            joined = projects.filter(statuses__status__iexact='joined').count()

            net_joined = joined - projects.filter(statuses__is_current=True, statuses__status__in=terminated).count()

            data = {
                "title": "Monthly Project joining Report &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse;width:99vw;height:99vh'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Status</th>
                                    <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em;">Joined</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em; text-align: center;">{joined}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em;">Net Joined</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em; text-align: center;">{net_joined}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em;">Total Offer</td>
                                    <td style="padding:5px 8px 5px 8px;font-size: 2.5em;font-size: 2.5em; text-align: center;">{total_projects}</td>
                                </tr>
                            </table>"""
            }
            payload = {
                "data": data, "report_name": "monthly_joining",
                "title": "Monthly Project joining Report :MEMO:",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_usa_joining_termination)
            # if msg == 'error':
            #     raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
