import csv
from datetime import datetime

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from project.models import ConsultantLeave, Project
from utils_app.models import Choice
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            current_year = datetime.now().year
            file = open("assign_leave.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["Consultant ID", "Consultant Name", "Assigned"])
            queryset = Project.objects.filter(
                statuses__status='joined', statuses__is_current=True, submission__work_type__in=['c2c', 'C2C']
            ).values_list('submission__consultant_marketing__consultant_id')
            project_consultant_ids = set(id for tup in queryset for id in tup)
            consultant_qs = Consultant.objects.filter(id__in=project_consultant_ids).distinct('id').order_by('id')

            leave_types = Choice.objects.filter(field='leave', content_type__model='consultantleave').exclude(
                name='covid_emergency_sick_leave'
            )
            for obj in consultant_qs:
                for leave in leave_types:
                    balance = 0
                    if leave.name == 'pto':
                        balance = 96
                    elif leave.name == 'sick_leave':
                        balance = 48
                    ConsultantLeave.objects.create(
                        year=current_year, balance=balance, granted=balance, consultant=obj, leave_type=leave
                    )
                writer.writerow([obj.id, obj.name, True])

            expired_leaves = ConsultantLeave.objects.exclude(year=current_year).filter(is_expired=False)
            for leave in expired_leaves:
                leave.is_expired = True
                leave.save()
        except Exception as e:
            print(str(e))
