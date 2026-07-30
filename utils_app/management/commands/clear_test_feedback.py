import csv

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from marketing.models import Test


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            tst = Test.objects.get(id=2767)
            tst.status = 'assigned'
            tst.engineer_remarks = None
            tst.engineer.clear()
            tst.save()

            feedbacks = tst.engineer_feedback.filter()
            for ans in feedbacks:
                ans.delete()

        except Exception as e:
            print(str(e))
