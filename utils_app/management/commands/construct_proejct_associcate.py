from django.core.management import BaseCommand

from project.models import Project
from project.utils import assign_project_associates
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    def handle(self, *args, **options):
        job = create_cron_object(name='construct_project_associate')
        try:
            projects = Project.objects.filter(
                statuses__status='joined', statuses__is_current=True, statuses__created__gte="2023-11-01"
            )
            for project in projects:
                po_hours = 0
                timesheet_qs = project.timesheets.filter(status='approved')
                for timesheet in timesheet_qs:
                    po_hours += timesheet.hours
                data = {"total_hours": po_hours}
                assign_project_associates(project, None, **data)
                print("Project associates created")
        except Exception as error:
            create_cron_error(job, error)
