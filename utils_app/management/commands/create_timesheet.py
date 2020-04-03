import logging
from django.db.models import Max
from datetime import datetime, timedelta
from django.core.management import BaseCommand

from project.models import Project, TimeSheet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is creating draft timesheet for weeks"

    # A command must define handle()
    def handle(self, *args, **options):
        projects = list(
            TimeSheet.objects.all().order_by('project_id').distinct('project_id').values_list('project_id', flat=True))
        count = 0
        end_date = datetime.today().date() + timedelta(days=2)
        for p in projects:
            project = Project.objects.get(id=p)
            last_timesheet = TimeSheet.objects.filter(project=project).aggregate(Max('end'))
            if last_timesheet['end__max'] is not None:
                end_date = last_timesheet['end__max']
            while end_date < datetime.today().date() + timedelta(days=30):
                timesheet, created = TimeSheet.objects.get_or_create(
                    hours=0,
                    project=project,
                    end=end_date + timedelta(days=7),
                    start=end_date + timedelta(days=1),
                )
                end_date = timesheet.end
        print(count)

