import logging
from django.utils import timezone
from django.db.models import Q, Max
from django.core.management import BaseCommand
from datetime import datetime, timedelta

from project.models import Project, TimeSheet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is creating draft timesheet for weeks"

    # A command must define handle()
    def handle(self, *args, **options):
        projects = Project.objects.filter(
            Q(end_date=None, statuses__status='joined', statuses__is_current=True) |
            Q(end_date__gte=timezone.now(), statuses__status='joined',  statuses__is_current=True)
        )
        end_date = datetime.today().date()
        for project in projects:
            last_timesheet = TimeSheet.objects.filter(project=project).aggregate(Max('end'))
            if last_timesheet['end__max'] is not None:
                end_date = last_timesheet['end__max']
            while end_date < datetime.today().date() + timedelta(days=7):
                timesheet, created = TimeSheet.objects.get_or_create(
                    hours=0,
                    project=project,
                    end=end_date + timedelta(days=7),
                    start=end_date + timedelta(days=1),
                )
                end_date = timesheet.end

