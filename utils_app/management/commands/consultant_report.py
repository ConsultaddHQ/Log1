import csv
from django.core.management import BaseCommand

from project.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open("consultant_report.csv", "w+")
            writer = csv.writer(file)
            header = ["ID", "Consultant Name", "Email", "Consultant Rate", "PO Rate", "Client", "Vendor", "Project Type"]
            writer.writerow(header)
            po_qs = Project.objects.filter(statuses__is_current=True, statuses__status='joined').order_by(
                "submission__consultant_marketing__consultant_id").distinct("submission__consultant_marketing__consultant_id")
            for obj in po_qs:
                writer.writerow([
                    obj.submission.consultant.id, obj.submission.consultant.name, obj.submission.consultant.email,
                    obj.submission.consultant.rate, obj.rate, obj.submission.client, obj.submission.vendor.name,
                    obj.submission.get_work_type_display()
                ])
        except Exception as error:
            print(error)