from constance import config
from django.core.management import BaseCommand

from utils_app.thred_mail import send_email
from utils_app.utils import create_cron_error, create_cron_object
from project.models import ProjectAssociates, DURATION_COMPLETION_NOTIFICATION_TYPE


class Command(BaseCommand):

    @staticmethod
    def send_project_completion_notification(obj, hours):
        try:
            submission = obj.project.submission
            mail_data = {
                "to": [config.FINANCE], "bcc": [],
                "cc": [obj.marketer.email, obj.vp.email],
                'template': '../templates/project_completion.html',
                'subject': f"Successful Completion of {obj.total_hours}-Hour on Project by Consultant "
                           f"{submission.consultant.name}",
                "context": {
                    "start_date": obj.project.start_date,
                    "vendor_company": submission.vendor.name,
                    "url": config.APP_URL, "consultant_name": submission.consultant.name,
                    "client_company": submission.client, "project_hours": obj.total_hours,
                    "redirection_url": f"{config.APP_URL}#/details/{submission.id}/project?id={obj.project_id}"
                }
            }

            if obj.lead_sm:
                mail_data.get("cc").append(obj.lead_sm.email)
            if obj.team_lead:
                mail_data.get("cc").append(obj.team_lead.email)

            support_persons = obj.project.support.filter(
                is_proxy_support=False, support__is_active=True).values_list('support__email', flat=True)
            if support_persons:
                mail_data["cc"].extend(support_persons)

            supervisors = obj.interviews.exclude(supervisor__employee_id=9999).exclude(
                supervisor__is_active=False).values_list('supervisor__email', flat=True)
            if supervisors:
                mail_data["cc"].extend(supervisors)

            coders = obj.interviews.exclude(guests__user__is_active=False).values_list('guests__user__email', flat=True)
            if coders:
                mail_data["cc"].extend(coders)

            msg, resp, _ = send_email(mail_data, "product@consultadd.com", None, False)
            return msg, resp, _
        except Exception as error:
            return f"{error} error while sending mail", False, None

    def handle(self, *args, **options):
        job = create_cron_object(name='project_duration_notification')
        try:
            for notification_type in DURATION_COMPLETION_NOTIFICATION_TYPE:
                check = {
                    'total_hours__lte': 1000,
                    'total_hours__gte': notification_type["hour"],
                    f'notification_type__{notification_type["du_check"]}': False,
                }
                associates_qs = ProjectAssociates.objects.filter(**check)
                for obj in associates_qs:
                    msg, resp, _ = self.send_project_completion_notification(obj, notification_type["hour"])
                    if resp:
                        obj.notification_type[notification_type["du_check"]] = True
                        obj.initial_notification = True
                        obj.save()
                    else:
                        create_cron_error(job, msg)

            associates_qs = ProjectAssociates.objects.filter(
                total_hours__gte=1000, initial_notification=True, secondary_notification=False
            )
            for obj in associates_qs:
                msg, resp, _ = self.send_project_completion_notification(obj, 1000)
                if resp:
                    obj.initial_notification = True
                    obj.secondary_notification = True
                    obj.save()
                else:
                    create_cron_error(job, msg)

        except Exception as error:
            create_cron_error(job, error)
