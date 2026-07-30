import os
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.core.management import BaseCommand

from marketing.models import Submission
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "this command is to move Consultant in pool"

    def handle(self, *args, **options):
        try:

            queryset = Submission.objects.all()
            for obj in queryset:
                if obj.created_by and obj.created_by.team:
                    obj.marketing_team = obj.created_by.team
                    obj.save()
        except Exception as error:
            print(str(error))
