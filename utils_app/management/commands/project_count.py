from datetime import date, datetime
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
        job = CronJob.objects.get(name='project_count')
        job.modified = datetime.now()
        job.save()
        try:
            cancelled = ['cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled',
                         'cancelled-contract_conflicts',
                         'cancelled-candidate_denied', 'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
                         'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location']

            terminated = ["completed", 'terminated', 'terminated-resigned', 'terminated-resigned_rate_issue',
                          'terminated-resigned_technology_issue', 'terminated-fired_budget_issue', 'terminated-fired',
                          'terminated-fired_security_issue', 'terminated-resigned_location_issue',
                          'terminated-fired_performance_issue', 'terminated-resigned_full_time_offer']

            last = date.today()
            first = date.today().replace(day=1)
            new_offer = Project.objects.filter(statuses__status='new', statuses__is_current=True).count()
            received_projects = Project.objects.filter(statuses__status='received', statuses__is_current=True).count()
            on_boarded_projects = Project.objects.filter(statuses__status='on_boarded',
                                                         statuses__is_current=True).count()
            joined_projects = Project.objects.filter(statuses__status='joined', statuses__is_current=True,
                                                     statuses__created__range=[first, last]).count()
            cancelled_projects = Project.objects.filter(statuses__status__in=cancelled, statuses__is_current=True,
                                                        created__range=[first, last]).count()
            terminated_projects = Project.objects.filter(statuses__status__in=terminated, statuses__is_current=True,
                                                         created__range=[first, last]).count()
            total_projects = Project.objects.filter(
                statuses__created__range=[first, last], statuses__is_current=True
            ).exclude(statuses__status__in=['new']).count()

            data = {
                "title": "Project Details &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;">Project Status</th>
                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">New Offer</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{new_offer}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Paper Work Received</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{received_projects}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">On-boarded</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{on_boarded_projects}</td>
                                </tr>
                            </table>"""
            }
            post_msg_using_webhook(config.announcement_url, data)

            data = {
                "title": "Business Health for this month &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>
                                <tr>
                                    <th style="padding:5px 8px 5px 8px;">Project Status</th>
                                    <th style="padding:5px 8px 5px 8px;">Count</th>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Joined</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{joined_projects}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Cancelled</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{cancelled_projects}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Terminated</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{terminated_projects}</td>
                                </tr>
                                <tr>
                                    <td style="padding:5px 8px 5px 8px;">Total Offer</td>
                                    <td style="padding:5px 8px 5px 8px;text-align: center;">{total_projects}</td>
                                </tr>
                            </table>"""
            }
            res, msg = post_msg_using_webhook(config.announcement_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
