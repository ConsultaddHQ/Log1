from datetime import date
from django.core.management import BaseCommand

from constants import pool_channel_url
from consultant.models import Consultant, ConsultantMarketing
from utils_app.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        in_pool_con = ConsultantMarketing.objects.filter(
            in_pool=True,
            end=None
        ).order_by('-marketing_start')

        count = 1
        text = f"""
#### Pool Candidates :beach_umbrella: \n
| # | Consultant | Team   | Days | Skills | Recruiter | Marketer |
|:--|:-----------|:-------|:-----|:-------|:----------|:---------|
"""
        for con in in_pool_con:
            days, marketer, recruiter = None, None, None
            team = ", ".join(con.teams.all().values_list('name', flat=True))
            if con.start:
                days = (date.today() - con.start).days
            if con.primary_marketer:
                marketer = con.primary_marketer.employee_name
            if con.recruiter:
                recruiter = con.recruiter.employee_name
            count += 1

            text += \
f"""| {count} | {con.consultant.name} | {team} | {days} | {con.consultant.skills} | {recruiter} | {marketer} |\n"""

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": text
        }

        post_msg_using_webhook(pool_channel_url, data)
