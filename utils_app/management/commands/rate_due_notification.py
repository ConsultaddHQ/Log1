import os

import csv
from datetime import date, timedelta
from django.core.management import BaseCommand

from employee.models import User
from project.models import Project
from utils_app.thred_mail import send_email_attachment_multiple
from consultant.models import Consultant, ConsultantRateRevision, ConsultantPOC
from utils_app.utils import create_cron_error, create_cron_object, delete_temp_file


class Command(BaseCommand):
    help = "This command is for sending Consultant rate due notification mail"

    def handle(self, *args, **options):
        job = create_cron_object(name='rate_due_notification')
        try:
            data = []
            counter = 1
            consultants = Consultant.objects.filter(status__in=['on_project'])
            file = open('consultant_rate_revision.csv', 'w+')
            writer = csv.writer(file)
            writer.writerow([
                'Consultant Name', 'Marketer Name', 'Vendor Name', 'Last Revised Date', 'Margin', "Project rate", 'Consultant rate'
            ])
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
                if (date.today() - timedelta(days=150) > revision_date) and margin_percentage < 22:
                    consultant_info = {
                        "counter": counter,
                        "po_rate": project_rate,
                        "rate": consultant_rate,
                        "consultant_id": consultant.id,
                        "last_revision": revision_date,
                        "consultant_name": consultant.name,
                        "consultant_email": consultant.email,
                        "marketer_name": marketer.get('name'),
                        "marketer_email": marketer.get('email'),
                        "margin": f"{margin}({margin_percentage}%)",
                        'vendor_name': project.submission.lead.vendor_company.name
                    }
                    writer.writerow([
                        consultant_info['consultant_name'], consultant_info['marketer_name'], consultant_info['vendor_name'],
                        consultant_info['last_revision'], consultant_info['margin'], consultant_info['po_rate'], consultant_info['rate']
                    ])
                    data.append(consultant_info)
                    counter += 1
            file.close()
            file = open(file.name, 'r')
            if os.environ.get('ENV', 'local') == 'prod':
                to = ['finance@consultadd.com',  'relations@consulatdd.com', 'arun.k@consultadd.com']
                scrum_master = User.objects.filter(
                    team__dept='Marketing', role__name='admin', is_active=True
                ).values_list('email', flat=True)
                to.extend(scrum_master)
            else:
                to = ['suman.m@consultadd.com', 'shreyas.k@consultadd.com', 'shivam.k@consultadd.com']
            mail_data = {
                'attachments': [file.name],
                'to': to, 'cc': [], 'bcc': [],
                'subject': f"Consultant Rate Revision Due Info",
                'template': '../templates/rate_due_notification.html',
                'context': {
                    "data": data,
                },
            }
            if len(data) > 0:
                send_email_attachment_multiple(mail_data, "product@consultadd.com", None, None, None, True)
            delete_temp_file([file.name])
        except Exception as error:
            print(error)
            create_cron_error(job, error)
