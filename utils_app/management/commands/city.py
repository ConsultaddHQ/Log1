import csv

from django.core.management import BaseCommand

from utils_app.models import City


class Command(BaseCommand):
    help = "This is one time command to move user avatar to AWS-S3 bucket"

    def handle(self, *args, **options):
        try:
            file = open('cities.csv', 'r')
            reader = csv.reader(file)
            i = 0
            for row in reader:
                if i == 0:
                    i += 1
                    continue
                try:
                    City.objects.create(
                        name=row[0], state=row[1], country='CA'
                    )
                except Exception as e:
                    print(row)
                    i += 1
                    continue
                i += 1
        except Exception as error:
            print(error)
