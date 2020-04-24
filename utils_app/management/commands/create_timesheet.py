import logging
from django.db.models import Max
from datetime import datetime, timedelta
from django.core.management import BaseCommand

from project.models import TimeSheet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is creating draft timesheet for weeks"

    # A command must define handle()
    def handle(self, *args, **options):
        timesheets = TimeSheet.objects.all().order_by('project_id').distinct('project_id')
        count = 0
        end_date = datetime.today().date()
        for t in timesheets:
            project = t.project
            last_timesheet = TimeSheet.objects.filter(project=project).aggregate(Max('end'))
            if last_timesheet['end__max'] is not None:
                end_date = last_timesheet['end__max']

            if project.statuses.filter(is_current=True, status__istartswith='terminated'):
                if end_date + timedelta(days=7) > project.end_date:
                    continue

            while end_date <= datetime.today().date():
                timesheet, created = TimeSheet.objects.get_or_create(
                    project=project,
                    end=end_date + timedelta(days=7),
                    start=end_date + timedelta(days=1),
                )
                if created:
                    timesheet.hours = 0
                    timesheet.save()
                end_date = end_date + timedelta(days=7)
        print(count)

