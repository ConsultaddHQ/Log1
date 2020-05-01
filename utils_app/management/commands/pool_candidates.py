from datetime import date
from django.core.management import BaseCommand

from constance import config
from consultant.models import ConsultantMarketing
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        in_pool_con = ConsultantMarketing.objects.filter(
            in_pool=True,
            status='open'
        ).order_by('consultant_id', '-start').distinct('consultant_id')

        count = 1
        text = f"""
#### Pool Candidates :beach_umbrella: \n
| # | Consultant | Team   | Days | Recruiter | Marketer |  Skills |Open Offer |
|:--|:-----------|:-------|:-----|:----------|:---------|:--------|:-----------|
"""
        for con in in_pool_con:
            if con.consultant.status != 'archived':
                days, marketer, recruiter, open_offer = None, None, None, "NO"
                team = ", ".join(con.teams.all().values_list('name', flat=True))
                if con.start:
                    days = (date.today() - con.start).days
                if con.primary_marketer:
                    marketer = con.primary_marketer.employee_name
                if con.recruiter:
                    recruiter = con.consultant.recruiter.employee_name
                open_offer_count = con.consultant.projects.filter(
                    statuses__is_current=True, statuses__status__in=['on_boarding', 'received']
                ).count()
                count += 1

                text += \
f"""| {count} | {con.consultant.name} | {team} | {days} | {recruiter} | {marketer} | {con.consultant.skills} | {open_offer_count}|\n"""

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        post_msg_using_webhook(config.pool_channel_url, data)
