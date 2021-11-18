import os

from django.db.models import Q
from datetime import date, timedelta
from django.core.management import BaseCommand

from project.models import Project
from log1.utils import write_exception
from utils_app.mailing import send_email
from consultant.models import Consultant, ConsultantRateRevision
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='bench_count')
        try:
            data = []
            consultants = Consultant.objects.filter(status__in=['on_bench', 'on_project'])
            for count, consultant in enumerate(consultants):
                try:
                    rate_qs = ConsultantRateRevision.objects.filter(consultant_id=consultant.id, end=None)
                    if rate_qs:
                        revision_date = rate_qs.first().start
                    else:
                        revision_date = date(2010, 1, 1)
                    projects = Project.objects.filter(
                        (
                                Q(consultant_id=consultant.id) |
                                Q(submission__consultant_marketing__consultant_id=consultant.id)
                        ) & (
                            Q(statuses__status='joined')
                        )
                    )
                    for project in projects:
                        if revision_date < project.start_date:
                            revision_date = project.start_date
                    if date.today() + timedelta(days=170) > revision_date:
                        data.append({
                            "count": count,
                            "consultant_id": consultant.id,
                            "consultant_name": consultant.name,
                            "consultant_email": consultant.email,
                        })
                except Exception as error:
                    write_exception(message=error)

            if os.environ.get('ENV', 'local') == 'prod':
                to = ['finance@consultadd.com']
            else:
                to = ['sarang.m@consultadd.com']
            mail_data = {
                'to': to, 'cc': [], 'bcc': [],
                'subject': f"Consultant Rate Revision Due",
                'template': '../templates/rate_due_notification.html',
                'context': {
                    "data": data,
                },
            }
            if len(data) > 0:
                send_email(mail_data, "admin@consultadd.com")
        except Exception as error:
            create_cron_error(job, error)
