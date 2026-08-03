import csv
import json

from django.core.management import BaseCommand

from marketing.models import VendorCompany


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            with open("dbvendorcompany.json", "w") as dbvendorfile:
                vendor_list = list(VendorCompany.objects.all().values("id", "name"))
                json.dump(vendor_list, dbvendorfile, indent=2)

            with open("vendorcompany.csv", "r") as vendorfile:
                reader = csv.DictReader(vendorfile)
                data = [row for row in reader]
                with open("vendorcompany.json", mode='w', encoding='utf-8') as json_file:
                    json.dump(data, json_file, indent=4)
        except Exception as error:
            print(error)