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
            "response_type": "in_channel",
            "username": "Log1 Updates",
            "text": f"""
#### Projects joining status :memo: \n
| Project Status                     | Count                    | 
|:-----------------------------------|:-------------------------|
| Joined Last Month                  | {joined_last_month}      |
| Joined This Month | {joined_this_month_t}/{joined_this_month} |
| Expected Joining this Month        | {expected_joining}       |
| Joining Status Not updated in log1 | {offers_not_joined}      |
"""
        }
        mattermost_webhook(config.joined_url, data)
