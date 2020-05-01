from datetime import date
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help Daily
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        month = date.today().month
        year = date.today().year

        terminated = ["completed", "resigned-rate", "resigned-location", "resigned-full_time", "resigned-technology",
                      "client-fired-budget", "client-fired-performance", "client-fired-security", "terminated"]

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
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Monthly Project joining Report :memo: \n
| Status      |      Count       | 
|:------------|:-----------------|
| Joined      | {joined}         |
| Net Joined  | {net_joined}     |
| Total Offer | {total_projects} |
"""
        }
        post_msg_using_webhook(config.joined_url, data)
