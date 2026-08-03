import csv
from datetime import date, datetime, timedelta

from constance import config
from django.core.management import BaseCommand
from django.db.models import Q

from employee.models import User
from project.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            file = open("OfferReport.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "PO ID", "Client", "Consultant Name", "Consultant Email", "Consultant Contact Number", "Project Type",
                "Job Title", "Start Date", "Vendor Name", "Vendor Contact Details", "Current Status",
                "Offer Received At", "Offer Year"
            ])
            po_qs = Project.objects.filter(
                Q(statuses__status__in=['joined', 'complete'], statuses__is_current=True) |
                Q(statuses__status__istartswith='terminated', statuses__is_current=True)
            ).filter(created__gt='2021-12-31')
            for obj in po_qs:
                job_position = obj.submission.lead.position.display_name \
                    if obj.submission.lead.position else obj.submission.lead.job_title
                vendor_contact = obj.submission.vendor_contact.number \
                    if obj.submission.vendor_contact else obj.submission.vendor.vendors.filter().first().number
                receive_date_obj = obj.statuses.filter(status='received').first()
                if receive_date_obj:
                    receive_date = receive_date_obj.created.date()
                    receive_year = receive_date_obj.created.date().year
                else:
                    receive_date = None
                    receive_year = None
                writer.writerow([
                    obj.id, obj.submission.client, obj.submission.consultant.name, obj.submission.consultant.email,
                    obj.submission.consultant.phone_no, obj.submission.get_work_type_display(), job_position,
                    obj.start_date, obj.submission.vendor.name, vendor_contact, obj.status, receive_date, receive_year
                ])
        except Exception as error:
            print(error)
