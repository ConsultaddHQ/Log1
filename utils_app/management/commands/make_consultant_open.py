import os
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.core.management import BaseCommand

from consultant.models import ConsultantMarketing
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "this command is to move Consultant in pool"

    def handle(self, *args, **options):
        job = create_cron_object(name='make_consultant_open')
        try:
            upper_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS')))
            lower_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS')) + 1)

            queryset = ConsultantMarketing.objects.filter(
                Q(status='open') &
                Q(start__lte=upper_limit) &
                Q(start__gte=lower_limit)
            ).exclude(status='terminated')

            for consultant_marketing in queryset:
                consultant_marketing.in_pool = True
                consultant_marketing.save()
        except Exception as error:
            create_cron_error(job, error)
