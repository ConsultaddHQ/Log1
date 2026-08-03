import csv
from django.core.management import BaseCommand

from marketing.models import Submission


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            file = open('vc.csv', 'w+')
            writer = csv.writer(file)
            writer.writerow([
                'Vendor ID', 'Vendor Contact Name', 'Vendor Contact Email', 'Vendor Contact Number', 'Work Type',
                'Vendor Company', 'Created By'
            ])
            submission_qs = Submission.objects.filter(marketing_team__name='Pythonwise').order_by('vendor_contact_id').distinct('vendor_contact_id')
            for obj in submission_qs:
                if not obj.vendor_contact:
                    continue
                vc = obj.vendor_contact
                writer.writerow([
                    vc.id, vc.name, vc.email, vc.number, obj.get_work_type_display(), vc.company.name, vc.created_by.employee_name
                ])
        except Exception as error:
            print(error)
