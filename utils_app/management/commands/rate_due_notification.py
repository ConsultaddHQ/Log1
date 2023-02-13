import os

import csv
from datetime import date, timedelta
from django.core.management import BaseCommand

from project.models import Project
from log1.utils import write_exception
from utils_app.mailing import send_email
from consultant.models import Consultant, ConsultantRateRevision, ConsultantPOC
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for sending Consultant rate due notification mail"

    def handle(self, *args, **options):
        job = create_cron_object(name='rate_due_notification')
        try:
            data = []
            consultants = Consultant.objects.filter(status__in=['on_project'])
            file = open('consultant_rate_revision.csv', 'w+')
            writer = csv.writer(file)
            writer.writerow(
                ['Consultant Name', 'Marketer Name', "Project rate", 'Consultant rate', 'DOJ', 'Last Revised Date',
                 'Vendor Name']
            )
            for consultant in consultants:
                last_revision = ConsultantRateRevision.objects.filter(consultant_id=consultant.id, end=None).first()
                if last_revision:
                    consultant_rate = last_revision.rate
                    revision_date = last_revision.start
                else:
                    consultant_rate = 0
                    revision_date = date(2010, 1, 1)
                project = Project.objects.filter(
                    is_remote=False, statuses__status='joined', statuses__is_current=True
                ).select_related('submission').filter(submission__consultant_marketing__consultant_id=consultant.id,
                                                      ).order_by('-rate').first()
                if not project:
                    continue
                project_rate = project.rate
                if revision_date < project.start_date:
                    revision_date = project.start_date
                margin = project_rate - consultant_rate
                margin_percentage = round((margin / project_rate) * 100, 2)
                marketer = {}
                assigned_marketer = ConsultantPOC.objects.filter(
                    poc_type='marketer', consultant_id=consultant.id, end=None).first()
                if not assigned_marketer:
                    marketer['name'] = project.submission.created_by.employee_name
                    marketer['email'] = project.submission.created_by.email
                else:
                    marketer['name'] = assigned_marketer.poc.employee_name
                    marketer['email'] = assigned_marketer.poc.email
                if (date.today() - timedelta(days=170) < revision_date) and margin_percentage < 23:
                    consultant_info = {
                        "rate": consultant_rate,
                        "po_rate": project_rate,
                        "doj": project.start_date,
                        "consultant_id": consultant.id,
                        "margin": f"{margin_percentage}%",
                        "consultant_name": consultant.name,
                        "consultant_email": consultant.email,
                        "marketer_name": marketer.get('name'),
                        "marketer_email": marketer.get('email'),
                        'vendor_name': project.submission.lead.vendor_company.name
                    }
                    writer.writerow([
                        consultant_info['consultant_name'], consultant_info['marketer_name'],
                        consultant_info['po_rate'], consultant_info['rate'], consultant_info['po_start_date'],
                        consultant_info['last_revision'], consultant_info['vendor_name']
                    ])
                    data.append(consultant_info)
            # if os.environ.get('ENV', 'local') == 'prod':
            #     to = ['finance@consultadd.com']
            # else:
            #     to = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']
            # mail_data = {
            #     'to': to, 'cc': [], 'bcc': [],
            #     'subject': f"Consultant Rate Revision Due",
            #     'template': '../templates/rate_due_notification.html',
            #     'context': {
            #         "data": data,
            #     },
            # }
            # if len(data) > 0:
            #     send_email(mail_data, "admin@consultadd.com")
        except Exception as error:
            print(error)
