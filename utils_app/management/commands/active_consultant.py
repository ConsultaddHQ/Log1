import csv
from datetime import timedelta
from django.core.management import BaseCommand

from consultant.models import Consultant
from project.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        file = open("consultant_details.csv", "w+")
        writer = csv.writer(file)
        writer.writerow([
            "Consultant Name", "Consultant Email", "Phone Number", "On Project", "Current Status", "Reason of Exit",
            "Total Active Duration more than 2 years", "Visa Status"
        ])
        try:
            queryset = Project.objects.exclude(submission__status__iexact='archive').exclude(
                submission__consultant_marketing__consultant__internal_employee=True
            ).order_by("submission__consultant_marketing__consultant").distinct(
                "submission__consultant_marketing__consultant"
            ).values_list("submission__consultant_marketing__consultant", flat=True)
            for consultant_id in queryset:
                obj = Consultant.objects.get(id=consultant_id)
                project = Project.objects.filter(
                    statuses__status="joined", statuses__is_current=True,
                    submission__consultant_marketing__consultant=obj
                ).first()
                if project:
                    on_project = True
                else:
                    on_project = False
                exit_qs = obj.exit.filter().first()
                if exit_qs:
                    reasons = ", ".join(exit_qs.reasons.filter().values_list('name', flat=True))
                    duration = exit_qs.created - obj.created
                    if duration > timedelta(days=730):  # approx 2 years
                        active_more_than_2_years = True
                    else:
                        active_more_than_2_years = False
                else:
                    reasons = None
                    active_more_than_2_years = None
                visa_status = obj.work_auth.filter().first().get_visa_type_display() if obj.work_auth.filter().first() else None
                writer.writerow([
                    obj.name, obj.email, obj.phone_no, on_project, obj.status, reasons, active_more_than_2_years,
                    visa_status
                ])
        except Exception as error:
            print(error)
