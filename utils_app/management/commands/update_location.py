import csv
from django.core.management import BaseCommand

from consultant.models import Consultant, ConsultantMarketing
from utils_app.models import Choice, ContentType


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            consultant_qs = Consultant.objects.filter().order_by('modified')
            for obj in consultant_qs:
                if obj.current_city:
                    location = obj.current_city.split(',')
                    if len(location) > 1:
                        obj.current_city = f'{location[0].replace(" ", "")},{location[1].replace(" ", "")}'
                        obj.save()

            cm_qs = ConsultantMarketing.objects.filter().order_by('modified')
            for obj in cm_qs:
                if obj.preferred_location:
                    location = obj.preferred_location.split(',')
                    if len(location) > 1:
                        obj.preferred_location = f'{location[0].replace(" ", "")},{location[1].replace(" ", "")}'
                        obj.save()

        except Exception as error:
            print(error)
