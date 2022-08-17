import csv

from django.core.management import BaseCommand

from utils_app.models import City
from consultant.models import Consultant


class Command(BaseCommand):
    help = "This is one time command to move user avatar to AWS-S3 bucket"

    def handle(self, *args, **options):
        try:
            consultants = Consultant.objects.exclude(current_city=None)
            count = 1
            for consultant in consultants:
                city = City.objects.filter(name=consultant.current_city.split(',')[0]).first()
                if city and city.country:
                    consultant.country = city.country
                    consultant.save()
                else:
                    consultant.country = "USA"
                    consultant.save()
                count += 1
            print(count)
        except Exception as error:
            print(error)
