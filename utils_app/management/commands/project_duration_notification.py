from constance import config
from django.core.management import BaseCommand

from utils_app.thred_mail import send_email
from project.models import ProjectAssociates
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    @staticmethod
    def send_project_completion_notification(obj, hours):
        try:
            submission = obj.project.submission
            mail_data = {
                "to": [config.FINANCE], "bcc": [],
                'template': '../templates/project_completion.html',
                'subject': f"Congratulations!!! {submission.consultant.name}'s project with {submission.client} completed {hours}",
                "cc": [obj.marketer.email, obj.vp.email, obj.team_lead.email, obj.lead_sm.email],
                "context": {
                    "vendor_company": submission.vendor.name,
                    "url": config.APP_URL, "consultant_name": submission.consultant.name,
                    "client_company": submission.client, "project_hours": obj.total_hours,
                    "redirection_url": f"{config.APP_URL}/#/details/{submission.id}/project?id={obj.project_id}"
                }
            }

            support_persons = obj.project.support.filter(
                is_proxy_support=False, support__is_active=True).values_list('support__email', flat=True)
            if support_persons:
                mail_data["cc"].extend(*support_persons)

            supervisors = obj.interviews.exclude(supervisor__employee_id=9999).exclude(
                supervisor__is_active=False).values_list('supervisor__email', flat=True)
            if supervisors:
                mail_data["cc"].extend(*supervisors)

            coders = obj.interviews.exclude(guests__is_active=False).values_list('guests__user__email', flat=True)
            if coders:
                mail_data["cc"].extend(*coders)

            msg, resp, _ = send_email(mail_data, "product@consultadd.com", None, True)
            return msg, resp, _
        except Exception as error:
            return f"{error} error while sending mail", False, None

    def handle(self, *args, **options):
        job = create_cron_object(name='project_duration_notification')
        try:
            associates_qs = ProjectAssociates.objects.filter(total_hours__gte=160, initial_notification=False)
            for obj in associates_qs:
                msg, resp, _ = self.send_project_completion_notification(obj, 160)
                if resp:
                    obj.initial_notification=True
                    obj.save()
                else:
                    create_cron_error(job, msg)

            associates_qs = ProjectAssociates.objects.filter(
                total_hours__gte=1000, initial_notification=True, secondary_notification=False
            )
            for obj in associates_qs:
                self.send_project_completion_notification(obj, 1000)
                msg, resp, _ = self.send_project_completion_notification(obj, 160)
                if resp:
                    obj.secondary_notification = True
                    obj.save()
                else:
                    create_cron_error(job, msg)

        except Exception as error:
            create_cron_error(job, error)
