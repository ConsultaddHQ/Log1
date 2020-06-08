from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()

    def handle(self, *args, **options):
        cancelled = ['cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled', 'cancelled-contract_conflicts',
                     'cancelled-candidate_denied', 'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
                     'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location']

        terminated = ["completed", 'terminated', 'terminated-resigned', 'terminated-resigned_rate_issue',
                      'terminated-resigned_technology_issue', 'terminated-fired_budget_issue', 'terminated-fired',
                      'terminated-fired_security_issue', 'terminated-resigned_location_issue',
                      'terminated-fired_performance_issue', 'terminated-resigned_full_time_offer']

        month = date.today().month
        new_offer = Project.objects.filter(statuses__status='new', statuses__is_current=True).count()
        received_projects = Project.objects.filter(statuses__status='received', statuses__is_current=True).count()
        on_boarded_projects = Project.objects.filter(statuses__status='on_boarded', statuses__is_current=True).count()
        joined_projects = Project.objects.filter(statuses__status='joined', statuses__is_current=True,
                                                 statuses__created=month).count()
        cancelled_projects = Project.objects.filter(statuses__status__in=cancelled, statuses__is_current=True,
                                                    created__month=month).count()
        terminated_projects = Project.objects.filter(statuses__status__in=terminated, statuses__is_current=True,
                                                     created__month=month).count()
        total_projects = Project.objects.filter(statuses__created__month=month, statuses__is_current=True).exclude(
            statuses__status__in=['new']).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Project Details :memo: \n
| Project Status     | Count   | 
|:--------------------|:-----------|
| New Offer | {new_offer} |
| Paper Work Received | {received_projects} |
| On boarded | {on_boarded_projects} |
"""
        }
        post_msg_using_webhook(config.offer_url, data)

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Business Health for this month :memo: \n
| Project Status    |  Count  | 
|:--------------------|:-----------|
| Joined  | {joined_projects} |
| Cancelled   | {cancelled_projects} |
| Terminated   | {terminated_projects} |
| Total Offer  | {total_projects} |
"""
        }
        post_msg_using_webhook(config.offer_url, data)
