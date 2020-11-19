from django.core.management import BaseCommand
from datetime import timedelta, date

from constance import config
from consultant.models import Consultant
from utils_app.mailing import send_email_without_template


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        thirty_days = date.today() + timedelta(days=30)
        fifteen_days = date.today() + timedelta(days=15)
        consultants = Consultant.objects.filter(marketing__status='open').exclude(
            status__in=['archived', 'terminated']
        ).distinct()
        for consultant in consultants:
            marketers = []
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
                        'cc': marketers,
                        'to': [config.RECRUITMENT, config.RELATIONS],
                        'subject': f"{consultant.name}'s Visa expiry reminder",
                        'body': f"Reminder: \n{visa.get_visa_type_display()} for {consultant.name} ({consultant.email})"
                                f" is expiring on {expiry_date}"
                    }
                    send_email_without_template(mail_data, "log1@consultadd.com")
