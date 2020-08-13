import os
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from django.core.management import BaseCommand

from consultant.models import ConsultantMarketing


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is to move Consultant in pool"

    # A command must define handle()
    def handle(self, *args, **options):
        upper_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS')))
        lower_limit = timezone.now().date() - timedelta(days=int(os.environ.get('DAYS'))+1)

        queryset = ConsultantMarketing.objects.filter(
            Q(status='open') &
            Q(start__lte=upper_limit) &
            Q(start__gte=lower_limit)
        ).exclude(status='archived')

        for consultant_marketing in queryset:
            consultant_marketing.in_pool = True
            consultant_marketing.save()
