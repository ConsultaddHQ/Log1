import csv

from django.db.models import Q
from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from notification.models import Notification
from project.models import ProjectSupport, Project, SupportStatus
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_consultant_leave')
        try:
            # noti = Notification.objects.all()
            file = open(f'support_info.csv', 'w')
            projects = Project.objects.filter((Q(statuses__status__istartswith='terminated') |
                                Q(statuses__status__istartswith='cancelled') | Q(statuses__status='complete')
                        ), statuses__is_current=True)
            writer = csv.writer(file)
            writer.writerow(
                ['project_id', 'consultant name', 'support name', 'support count', 'Is Remote', 'Start Date', 'status', 'end date']
            )
            for obj in projects:
                status = obj.statuses.filter(is_current=True).first()
                if status:
                    name=status.get_status_display()
                else:
                    name=None
                total_support = ProjectSupport.objects.filter(project=obj)
                supports = total_support.filter(statuses__frequency__in=['active', 'less_active'],
                                                statuses__is_current=True)
                for support in supports:
                    writer.writerow([obj.id, obj.consultant.name, support.support.employee_name, len(total_support),
                                     obj.is_remote, obj.start_date, name, support.end])
                    current_status = support.statuses.filter(is_current=True).first()
                    current_status.is_current = False
                    current_status.save()
                    SupportStatus.objects.create(frequency='independent', is_current=True, support=support)
        except Exception as error:
            print(error)
