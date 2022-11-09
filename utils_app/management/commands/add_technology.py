import csv
from django.core.management import BaseCommand

from consultant.models import Consultant
from employee.models import Certificate
from utils_app.utils import create_cron_error, create_cron_object, get_timezone
from utils_app.models import Choice, ContentType


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='add_technology')
        try:
            i = 0
            file = open('certification_list.csv', 'r')
            data = csv.reader(file)
            for item in data:
                if i == 0:
                    i += 1
                    continue
                Certificate.objects.create(name=item[0], issued_by=item[1])
                i += 1
        except Exception as error:
            print(error)
