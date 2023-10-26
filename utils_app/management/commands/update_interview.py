from datetime import timedelta, date
from django.core.management import BaseCommand

from marketing.models import Interview
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is to move Interview to failed after 30 days if status is feedback_due"

    def handle(self, *args, **options):
        job = create_cron_object('make_consultant_open')
        try:
            thirty_days = date.today() + timedelta(days=30)
            interviews = Interview.objects.filter(status='feedback_due')
            for interview in interviews:
                if interview.start_time == thirty_days:
                    interview.status = 'failed'
                    interview.failure_reason = 'system_updated'
                    interview.save()
        except Exception as error:
            create_cron_error(job, error)
