import os
from datetime import timedelta, date
from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object
from utils_app.mailing import send_email, send_email_without_template


class Command(BaseCommand):
    # Show this when the user types help
    help = "This command is to send mail for Visa expiry reminder"

    # A command must define handle()
    def handle(self, *args, **options):
        job = create_cron_object(name='visa_update_reminder')
        try:
            mail_error = []
            thirty_days = date.today() + timedelta(days=30)
            fifteen_days = date.today() + timedelta(days=15)

            consultants = Consultant.objects.filter(status='on_bench')
            for consultant in consultants:
                marketers = list()
                queryset = consultant.marketing.filter(status='open')
                if queryset:
                    marketers = [marketer.email for marketer in queryset.first().marketer.all()]
                work_auth = consultant.work_auth.filter(is_current=True).exclude(visa_end=None)
                if work_auth:
                    visa = work_auth.first()
                    expiry_date = visa.visa_end
                    if expiry_date == fifteen_days or expiry_date == thirty_days:
                        mail_data = {
                            'bcc': [],
                            'cc': marketers + [config.SUPERADMIN],
                            'to': [config.RECRUITMENT, config.RELATIONS],
                            'subject': f"Reminder: Visa is expiring: {consultant.name}",
                            'body': f"{consultant.name} {visa.get_visa_type_display()} is expiring on {expiry_date} "
                                    f"Please Update the work authorisation on log1."
                        }
                        res, ok = send_email_without_template(mail_data, "log1@consultadd.com")
                        if not ok:
                            mail_error.append((consultant.id, res))
            if len(mail_error) > 0:
                create_cron_error(job, mail_error)

            data = []
            consultants = Consultant.objects.exclude(status__in=['on_bench', 'terminated'])
            for consultant in consultants:
                work_auth = consultant.work_auth.filter(is_current=True).exclude(visa_end=None)
                if work_auth:
                    visa = work_auth.first()
                    expiry_date = visa.visa_end
                    if expiry_date == fifteen_days or expiry_date == thirty_days:
                        data.append({'name': consultant.name.title(), 'end_date': expiry_date})

            if consultants:
                if os.environ.get('env', 'local') == 'prod':
                    to = [config.SUPERADMIN, config.RECRUITMENT, config.RELATIONS]
                else:
                    to = ['sarang.m@consultadd.com']
                mail_data = {
                    'to': to, 'cc': [], 'bcc': [],
                    'template': '../templates/visa_reminder.html',
                    'subject': f"Reminder: Visa expiry reminder of On-Project consultants",
                    'context': {'data': data}
                }
                res, ok = send_email(mail_data, "log1@consultadd.com")
                if not ok:
                    create_cron_error(job, res)

        except Exception as error:
            create_cron_error(job, error)
