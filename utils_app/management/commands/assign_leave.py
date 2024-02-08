import csv

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from project.models import ConsultantLeave, Project
from utils_app.models import Choice
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):

        try:
            file = open("assign_leave.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["Consultant Name", "Assigned"])
            # queryset = Project.objects.filter(statuses__status='joined', statuses__is_current=True).values_list('submission__consultant_marketing__consultant', 'consultant')
            queryset = Project.objects.filter(statuses__status='joined', statuses__is_current=True).values_list(
                'consultant', flat=True)
            project_consultant_ids = list(set(queryset))
            leave_types = Choice.objects.filter(field='leave', name__in=["marriage_leave", "paternity", "maternity"])
            # project_consultant_ids = set(id for tup in queryset for id in tup)
            # prev_consultants_qs = ConsultantLeave.objects.filter(year=2023).values_list('consultant', flat=True)
            # pre_consultant_ids = set(prev_consultants_qs)
            #
            # consultant_ids = list(pre_consultant_ids.union(project_consultant_ids))
            consultant_qs = Consultant.objects.filter(id__in=project_consultant_ids)
            for obj in consultant_qs:
                for leave in leave_types:
                    balance = 0
                    ConsultantLeave.objects.create(
                        year=2024, balance=balance, granted=balance, consultant=obj, leave_type=leave
                    )
                writer.writerow([obj.name, True])

            expired_leaves = ConsultantLeave.objects.exclude(year=2024).filter(is_expired=False)
            for leave in expired_leaves:
                leave.is_expired = True
                leave.save()
        except Exception as e:
            print(str(e))
