from datetime import date
from django.core.management import BaseCommand

from consultant.models import ConsultantExit
from consultant.utils import terminate_consultant
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for terminating consultants on last date"

    def handle(self, *args, **options):
        job = create_cron_object(name='terminate_consultant')
        try:
            queryset = ConsultantExit.objects.filter(last_date__lte=date.today(), status='in_process')
            for terminate in queryset:
                terminate_consultant(terminate, None)
        except Exception as error:
            create_cron_error(job, error)
