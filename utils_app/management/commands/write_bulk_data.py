import csv
from django.core.management import BaseCommand

from marketing.models import Submission


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            file = open("AttioDumpData.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "Consultant Name", "Client", "Vendor", "Position", "Work Type", "Rate",
                "Employer", "Interview Exist", "Project Exist", "Project Status", "Submission Status"
            ])
            submission_qs = Submission.objects.filter(
                employer="Consultadd", work_type__iexact="C2C", created__gt="2024-12-31", rate__isnull=False,
                client__isnull=False, vendor_contact__isnull=False, lead__vendor_company__isnull=False,
                lead__position__isnull=False
            ).order_by("id").distinct("id")
            breakpoint()
            for obj in submission_qs:
                interview_exist = obj.screening.exists()
                project_exist = getattr(obj, 'project', None)
                writer.writerow([
                    obj.consultant.name, obj.client, obj.vendor.name, obj.lead.position.display_name,
                    obj.get_work_type_display(), obj.rate, obj.employer, interview_exist, True if project_exist else False,
                    obj.get_status_display(), obj.project.status if project_exist else None
                ])
        except Exception as e:
            print(str(e))
