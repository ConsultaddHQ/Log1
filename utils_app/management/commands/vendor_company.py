import csv
from django.core.management import BaseCommand

from marketing.models import Submission, VendorCompany


class Command(BaseCommand):

    @staticmethod
    def check_final_status(obj):
        statuses = {"Offer": ['in_offer', 'project'], "Interview": ['interview'], "Submission": ['sub']}
        for status in statuses.keys():
            sub_qs = Submission.objects.filter(status__in=statuses.get(status), lead__vendor_company=obj)
            if sub_qs.first():
                return status
        return None

    def handle(self, *args, **options):
        try:
            file = open("VC_details.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["ID", "Vendor Company Name", "Created By", "Status"])
            vc_qs = VendorCompany.objects.all()
            for obj in vc_qs:
                status = self.check_final_status(obj)
                if status is None:
                    status = 'draft'
                writer.writerow([obj.id, obj.name, obj.created_by, status])
        except Exception as error:
            print(error)
