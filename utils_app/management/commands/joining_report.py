from datetime import date
from django.core.management import BaseCommand

from constance import config
from utils_app.views import mattermost_webhook
from project.models import Project, PayrollSchedule


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):

        terminated = ["resigned-rate", "resigned-location", "resigned-full_time", "resigned-technology", "completed",
                      "client-fired-budget", "client-fired-performance", "client-fired-security", "terminated"]

        month = date.today().month
        year = date.today().year
        if month == 1:
            last_month = 12
            last_year = year - 1
        else:
            last_year = year
            last_month = month - 1

        pay_month = month
        if date.today().day > 15:
            pay_month = month + 1

        current_pay_period = PayrollSchedule.objects.filter(processing_date__month=pay_month).first()
        start_day = current_pay_period.pay_period_start
        end_day = current_pay_period.pay_period_end

        joined_last_month = Project.objects.filter(
            statuses__status__iexact='joined', statuses__created__year=last_year, statuses__created__month=last_month
        ).order_by('id').distinct('id').count()

        joined_this_month = Project.objects.filter(
            statuses__status__iexact='joined', statuses__created__year=year, statuses__created__month=month
        ).order_by('id').distinct('id').count()

        expected_joining = Project.objects.filter(
            start_date__year=year, start_date__gte=date.today(), start_date__month=month
        ).count()

        joining_in_pay_period = Project.objects.filter(
            start_date__range=[start_day, end_day]
        ).exclude(statuses__status__in=terminated).count()

        offers_not_joined = Project.objects.filter(
            start_date__lt=date.today(),
        ).exclude(statuses__is_current=True, statuses__status__in=terminated + ['joined']).count()

        data = {
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Projects joining status :memo: \n
Pay Period - {str(start_day)} - {str(end_day)}\n
| Project Status                     | Count                   | 
|:-----------------------------------|:------------------------|
| Joined Last Month                  | {joined_last_month}     |
| Joined This Month                  | {joined_this_month}     |
| Expected Joining this Month        | {expected_joining}      |
| Expected Joining in Pay Period     | {joining_in_pay_period} |
| Joining Status Not updated in log1 | {offers_not_joined}     |
"""
        }
        mattermost_webhook(config.joined_url, data)
