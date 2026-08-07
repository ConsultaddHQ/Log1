import csv
from django.core.management import BaseCommand

from project.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open("new_joiners.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Employee Name", "Employee Team", "Employee Joining Date", "Client", "Vendor", "Rate", "Project Type",
                "Offer Date", "Joining Date"
            ])
            # offers_qs = Project.objects.filter(statuses__status='received', statuses__created__gt="2024-10-31").order_by(
            #     "submission__created_by__employee_name"
            # )
            offers_qs = Project.objects.filter(
                statuses__status='received', statuses__created__gt="2024-11-11",
                submission__created_by__date_joined__gte="2024-01-01"
            ).order_by("submission__created_by__employee_name")
            for obj in offers_qs:
                writer.writerow([
                    obj.submission.created_by.employee_name, obj.submission.marketing_team.name, obj.submission.created_by.date_joined.date(),
                    obj.submission.client, obj.submission.vendor.name, obj.submission.rate, obj.submission.get_work_type_display(),
                    obj.statuses.filter(status='received').first().created, obj.start_date
                ])
        except Exception as error:
            print(error)
