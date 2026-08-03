import csv
from django.core.management import BaseCommand

from marketing.models import Submission, VendorCompany, VendorContact


class Command(BaseCommand):

    @staticmethod
    def check_final_status(obj):
        statuses = {"Offer": ['in_offer', 'project'], "Interview": ['interview'], "Submission": ['sub']}
        for status in statuses.keys():
            sub_qs = Submission.objects.filter(status__in=statuses.get(status), lead__vendor_company=obj)
            if sub_qs.first():
                return status
        return None

    @staticmethod
    def get_work_types(obj):
        work_types = []
        sub_qs = Submission.objects.filter(lead__vendor_company=obj).exclude(status__in=['draft', 'archive'])
        for sub in sub_qs:
            work_type = sub.get_work_type_display()
            if work_type not in work_types and (work_type is not None or work_type != 'None'):
                work_types.append(work_type)
        return work_types

    @staticmethod
    def get_positions(obj):
        positions = []
        sub_qs = Submission.objects.filter(lead__vendor_company=obj).exclude(status__in=['draft', 'archive'])
        for sub in sub_qs:
            pos = sub.lead.position.display_name if sub.lead.position else sub.lead.job_title
            if pos not in positions:
                positions.append(pos)
        return positions

    @staticmethod
    def get_region(obj):
        regions = []
        sub_qs = Submission.objects.filter(lead__vendor_company=obj).exclude(status__in=['draft', 'archive'])
        for sub in sub_qs:
            region = 'Canada' if sub.marketing_team.name == 'Consultadd Canada' else "USA"
            if region not in regions:
                regions.append(region)
        return regions

    @staticmethod
    def get_vc_details(obj):
        vc_details = ""
        contact_qs = obj.vendors.all()
        for contact in contact_qs:
            vc_details += f"{contact.name} | {contact.email} | {contact.number} | {contact.source_link}"
            vc_details += "\n  "
        return vc_details

    def handle(self, *args, **options):
        try:
            file = open("VC_details.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "ID", "Vendor Company Name", "Created By", "Work Type", "Region", "Position", "Vendor Contact", "Status"
            ])
            vc_qs = VendorCompany.objects.all()
            for obj in vc_qs:
                status = self.check_final_status(obj)
                work_types = self.get_work_types(obj)
                position = self.get_positions(obj)
                regions = self.get_region(obj)
                vc = self.get_vc_details(obj)
                if status is None:
                    status = 'draft'
                writer.writerow([
                    obj.id, obj.name, obj.created_by, ", ".join(work_types), ", ".join(regions),
                    ", ".join(position), vc, status
                ])
        except Exception as error:
            print(error)
