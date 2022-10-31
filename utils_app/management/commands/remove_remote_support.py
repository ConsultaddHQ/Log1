import csv

from django.db.models import Q
from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from project.models import ProjectSupport, Project
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_consultant_leave')
        try:
            file = open(f'support.csv', 'w')
            # projects = Project.objects.filter((Q(statuses__status__istartswith='terminated') |
            #                                    Q(statuses__status__istartswith='canceled') |
            #                                    Q(statuses__status='complete')), statuses__is_current=True)
            #                                   start_date__gt='2022-03-31')
            projects = Project.objects.all().order_by('-start_date')
                # filter(start_date__gt='2022-03-31')
            writer = csv.writer(file)
            writer.writerow(
                ['project_id', 'consultant name', 'support name', 'support count', 'Is Remote', 'Start Date', 'status']
            )
            for obj in projects:
                total_support = ProjectSupport.objects.filter(project=obj)
                supports = total_support.filter(support__email=obj.consultant.email)
                support = supports.first()
                status = obj.statuses.filter(is_current=True).first()
                if status:
                    name=status.get_status_display()
                else:
                    name=None
                if support:
                    writer.writerow([obj.id, obj.consultant.name, support.support.employee_name, len(total_support),
                                     obj.is_remote, obj.start_date, name])
                    support.delete()
        except Exception as error:
            print(error)
