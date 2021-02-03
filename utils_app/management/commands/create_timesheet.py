from django.db.models import Max, Q
from datetime import datetime, timedelta
from django.core.management import BaseCommand

from project.models import TimeSheet


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is creating draft timesheet for weeks"

    # A command must define handle()
    def handle(self, *args, **options):
        timesheets = TimeSheet.objects.all().order_by('project_id').distinct('project_id')
        count = 0
        for timesheet in timesheets:
            project = timesheet.project
            last_timesheet = TimeSheet.objects.filter(project=project).aggregate(Max('end'))
            end_date = last_timesheet['end__max']
            if project.statuses.filter(Q(is_current=True) & (Q(status__istartswith='terminated') | Q(status='complete'))):
                continue
            while end_date <= datetime.today().date() + timedelta(days=30):
                # timesheet, created = TimeSheet.objects.get_or_create(
                #     project=project,
                #     end=end_date + timedelta(days=7),
                #     start=end_date + timedelta(days=1),
                # )
                # if created:
                #     timesheet.hours = 0
                #     timesheet.save()
                end_date = end_date + timedelta(days=7)
            count += 1
