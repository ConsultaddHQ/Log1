import csv
from django.core.management import BaseCommand
from django.db.models import Q

from project.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            file = open("consultant_remote_project.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "PO ID", "Consultant Name", "Consultant Email", "Consultant Phone Number", "Consultant Joining Date",
                "Consultant Exit Date", "Remote Engineer Name", "Client", "Vendor Company Name", "Work Type",
                "PO Start Date", "PO End Date", "PO Current Status"
            ])
            project_qs = Project.objects.filter(
                Q(statuses__status__in=['joined', 'complete']) | Q(statuses__status__istartswith='terminated'),
                is_remote=True
            ).order_by('-id').distinct('id')
            for obj in project_qs:
                consultant = obj.submission.consultant
                consultant_exit = consultant.exit.filter().order_by('-id').first()
                exit_date = None
                if consultant_exit:
                    exit_date = consultant_exit.resign_date if consultant_exit.resign_date else consultant_exit.last_date \
                        if consultant_exit.last_date else consultant_exit.created.strftime("%Y-%m-%d")
                writer.writerow([
                    obj.id, consultant.name, consultant.email, consultant.phone_no, consultant.created.strftime("%Y-%m-%d"),
                    exit_date, obj.consultant.name, obj.submission.client, obj.submission.lead.vendor_company.name,
                    obj.submission.get_work_type_display(), obj.start_date, obj.end_date, obj.status
                ])
        except Exception as error:
            print(error)
