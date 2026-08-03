import csv
from django.core.management import BaseCommand

from project.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            file = open("fix_po_data.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                "PO ID", "Submission Consultant", "Remote Engineer", "PO Type", "Is Remote", "Redirection"
            ])
            po_qs = Project.objects.filter(
                statuses__status__istartswith='terminated', statuses__created__range=['2023-01-01', '2024-12-01']
            )
            for po in po_qs:
                if po.consultant and po.submission.consultant != po.consultant:
                    if not po.is_remote:
                        po.is_remote = True
                        po.save()
                        writer.writerow([
                            po.id, po.submission.consultant.name, po.consultant.name, po.is_remote,
                            f"https://log1.com/#/details/{po.submission.id}/project?id={po.id}"
                        ])
        except Exception as error:
            print(error)
