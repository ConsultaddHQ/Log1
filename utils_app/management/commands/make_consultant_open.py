import os
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.management import BaseCommand

from utils_app.models import CronJob
from consultant.models import ConsultantMarketing


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is to move Consultant in pool"

    # A command must define handle()
    def handle(self, *args, **options):
        job = CronJob.objects.get(name='make_consultant_open')
        job.last_triggered_at = datetime.now()
        try:
            upper_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS')))
            lower_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS')) + 1)

            queryset = ConsultantMarketing.objects.filter(
                Q(status='open') &
                Q(start__lte=upper_limit) &
                Q(start__gte=lower_limit)
            ).exclude(status='archived')

            for consultant_marketing in queryset:
                consultant_marketing.in_pool = True
                consultant_marketing.save()
            job.last_status = 'complete'
        except Exception as error:
            job.last_status = 'failed'
            print(error)

        finally:
            job.save()
