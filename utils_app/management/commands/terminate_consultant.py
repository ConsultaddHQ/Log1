from datetime import date, datetime
from django.core.management import BaseCommand

from utils_app.models import CronJob
from consultant.models import ConsultantExit
from utils_app.utils import create_cron_error
from consultant.utils import terminate_consultant


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to Messaging app"

    def handle(self, *args, **options):
        job = CronJob.objects.get(name='terminate_consultant')
        job.modified = datetime.now()
        job.save()
        try:
            queryset = ConsultantExit.objects.filter(last_date__lte=date.today(), status='in_process')
            for terminate in queryset:
                terminate_consultant(terminate)
        except Exception as error:
            create_cron_error(job, error)
