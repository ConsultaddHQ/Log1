import logging
from django.db.models import Q
from django.utils import timezone
from django.core.management import BaseCommand
from datetime import datetime, timedelta

from project.models import Project, TimeSheet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is creating timesheet weeks"

    # A command must define handle()
    def handle(self, *args, **options):
        projects = Project.objects.filter(
            Q(end_date=None, statuses__status='joined', statuses__is_current=True) |
            Q(end_date__gte=timezone.now(), statuses__is_current=True)
        )
        end_date = datetime.today().date()
        for project in projects:
            last_timesheet = TimeSheet.objects.filter(project=project).latest('end')
            if last_timesheet:
                end_date = last_timesheet.end
            if end_date < datetime.today().date() + timedelta(days=7):
                TimeSheet.objects.get_or_create(
                    project=project,
                    start=end_date + timedelta(days=1),
                    end=end_date + timedelta(days=7),
                )
        logger.info(f"Timesheets Created for Week {end_date + timedelta(days=1)} to {end_date + timedelta(days=7)}")

