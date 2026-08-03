import csv
from django.core.management import BaseCommand

from marketing.models import Submission


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            file = open('vc.csv', 'w+')
            writer = csv.writer(file)
            writer.writerow([
                'Client Name', 'Vendor Company', 'Work Type', 'Vendor Contact Name', 'Vendor Contact Email',
                'Vendor Contact Number', 'Vendor Source Link', 'Created By'
            ])
            submission_qs = Submission.objects.all().exclude(
                client__iexact='TBD'
            ).order_by('vendor_contact_id').distinct('vendor_contact_id')
            for obj in submission_qs:
                vc = obj.vendor_contact
                if vc and obj.client:
                    writer.writerow([
                        obj.client, vc.company.name, obj.get_work_type_display(), vc.name, vc.email, vc.number,
                        vc.source_link, vc.created_by.employee_name
                    ])
        except Exception as error:
            print(error)
