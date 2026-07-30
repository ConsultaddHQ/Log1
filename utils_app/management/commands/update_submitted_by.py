import json
from marketing.models import Test
from django.core.management import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            count = 0
            queryset = Test.objects.all().order_by('modified')
            for obj in queryset:
                if obj.submitted_by:
                    associates = obj.engineer.filter(role__name='engineer')
                    if associates.first():
                        count += 1
                        obj.submitted_by = associates.first()
                        obj.save()
            print(count)
        except Exception as error:
            print(str(error))
