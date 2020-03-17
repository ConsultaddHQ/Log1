from datetime import date
from django.core.management import BaseCommand

from constance import config
from utils_app.views import mattermost_webhook
from project.models import Project, PayrollSchedule


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):

        month = date.today().month
        year = date.today().year
        if month == 1:
            last_month = 12
            year = year - 1
        else:
            year -= 1
            last_month = month - 1

        current_pay_period = PayrollSchedule.objects.filter(processing_date__month=month).first()
        start_day = current_pay_period.pay_period_start
        end_day = current_pay_period.pay_period_end

        joined_last_month = Project.objects.filter(
            statuses__status__iexact='joined', statuses__is_current=True,
            statuses__created__year=year, statuses__created__month=last_month,
        ).count()

        expected_joining = Project.objects.filter(
            start_date__day__gte=1,
            start_date__month=month,
        ).count()

        joining_in_pay_period = Project.objects.filter(
            start_date__range=[start_day, end_day],
        ).count()

        offers_not_joined = Project.objects.filter(
            start_date__lt=date.today(),
        ).exclude(statuses__is_current=True, statuses__status__iexact='joined').count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Project Details :memo: \n
| Project Status                 | Count             | 
|:-------------------------------|:------------------|
| Joined Last Month              | {joined_last_month} |
| Expected Joining this Month    | {expected_joining} |
| Expected Joining in Pay Period | {joining_in_pay_period} |
| Not Joined Yet                 | {offers_not_joined} |
"""
        }
        mattermost_webhook(config.offer_url, data)
