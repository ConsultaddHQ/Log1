from datetime import timedelta, date
from django.core.management import BaseCommand

from constance import config
from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object
from utils_app.thred_mail import send_email, send_email_without_template
# from utils_app.mailing import send_email_without_template


class Command(BaseCommand):
    help = "This command is to send mail for Visa expiry reminder"

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
                        try:
                            send_email_without_template(mail_data, "product@consultadd.com", None, None, True)
                        except Exception as e:
                            mail_error.append((consultant.id, f"mail not send {str(e)}"))
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
            if len(data) > 0:
                mail_data = {
                    'cc': [], 'bcc': ['shreyas.k@consultadd.com'],
                    'template': '../templates/visa_reminder.html',
                    'to': [config.SUPERADMIN, config.RECRUITMENT, config.RELATIONS],
                    'subject': f"Reminder: Visa expiry reminder of On-Project consultants",
                    'context': {'data': data}
                }
                res, ok, _ = send_email(mail_data, "product@consultadd.com", None, True)
                if not ok:
                    create_cron_error(job, res)

        except Exception as error:
            create_cron_error(job, error)
