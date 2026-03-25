import csv
from datetime import datetime

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType
from django.db.models import Count, Subquery, OuterRef

from project.models import ConsultantLeave, Project
from utils_app.models import Choice
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            # current_year = datetime.now().year
            file = open("assigned_leave.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(["Consultant ID", "Consultant Name", "Leave Type", "Granted"])
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
                        prev_leave_obj = ConsultantLeave.objects.filter(
                            year=2025, consultant=obj, leave_type=leave, on_hold=False
                        ).first()
                        if prev_leave_obj:
                            if prev_leave_obj.balance > 48:
                                balance = 96 + 48
                            else:
                                balance = 96 + prev_leave_obj.balance
                        else:
                            balance = 96
                        writer.writerow([obj.id, obj.name, leave.display_name, balance])
                    elif leave.name == 'sick_leave':
                        prev_leave_obj = ConsultantLeave.objects.filter(
                            year=2025, consultant=obj, leave_type=leave, on_hold=False
                        ).first()
                        if prev_leave_obj:
                            if prev_leave_obj.balance > 24:
                                balance = 48 + 24
                            else:
                                balance = 48 + prev_leave_obj.balance
                        else:
                            balance = 48
                        writer.writerow([obj.id, obj.name, leave.display_name, balance])
                    ConsultantLeave.objects.create(
                        year=2026, balance=balance, granted=balance, consultant=obj, leave_type=leave
                    )

            expired_leaves = ConsultantLeave.objects.exclude(year=2026).filter(is_expired=False)
            for leave in expired_leaves:
                leave.is_expired = True
                leave.save()
            # duplicate_count_subquery = (
            #     ConsultantLeave.objects
            #     .filter(
            #         year=2025,
            #         consultant=OuterRef('consultant'),
            #         leave_type=OuterRef('leave_type')
            #     )
            #     .values('consultant', 'leave_type')
            #     .annotate(cnt=Count('id'))
            #     .values('cnt')[:1]
            # )
            #
            # leaves = (
            #     ConsultantLeave.objects
            #     .filter(year=2025)
            #     .annotate(dup_count=Subquery(duplicate_count_subquery))
            #     .filter(dup_count__gt=1)
            # )
            # for obj in leaves:
            #     writer.writerow([
            #         obj.consultant.id, obj.consultant.name, obj.leave_type.display_name,
            #         obj.balance, obj.granted, obj.on_hold
            #     ])
        except Exception as e:
            print(str(e))
