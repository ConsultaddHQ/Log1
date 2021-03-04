from datetime import date, timedelta, datetime
from django.core.management import BaseCommand

from constance import config

from project.models import Project
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    def handle(self, *args, **options):
        job = CronJob.objects.get(name='monday_po_alert')
        job.last_triggered_at = datetime.now()
        try:
            end = date.today() - timedelta(days=1)
            start = date.today() - timedelta(days=7)

            text = f"<tr>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Consultant</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Team</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Client</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Vendor</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Marketer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Start Date</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Employer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>City</th>" \
                   f"</tr>"

            joined_last_week = Project.objects.filter(
                statuses__status__iexact='joined',
                start_date__range=[start, end],
                statuses__is_current=True,
            )
            for project in joined_last_week:
                submission = project.submission
                text += f"<tr>" \
                        f"<td style='padding:px 8px 0px 8px;'> {project.consultant.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.created_by.team.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.client} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.lead.vendor_company.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.created_by.employee_name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {project.start_date.strftime('%m/%d/%Y')} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.employer} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {project.city} </td>" \
                        f"</tr>\n"

            data = {
                "title": "Project Joined Last Week &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            post_msg_using_webhook(config.joined_url, data)

            text = f"<tr>" \
                   f"<th style='padding:2px 8px 0px 8px;'>Consultant</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Team</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Client</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Vendor</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Marketer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Start Date</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>Employer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;'>City</th>" \
                   f"</tr>"
            start = date.today()
            end = date.today() + timedelta(days=5)

            cancelled = ['cancelled-dual_offer', 'cancelled', 'cancelled-client_cancelled',
                         'cancelled-contract_conflicts',
                         'cancelled-candidate_denied', 'cancelled-candidate_absconded', 'cancelled-candidate_denied_jd',
                         'cancelled-candidate_denied_rate', 'cancelled-candidate_denied_location']

            joining_this_week = Project.objects.filter(start_date__range=[start, end]).exclude(
                statuses__status__in=cancelled,
                statuses__is_current=True,
            )

            for project in joining_this_week:
                submission = project.submission
                text += f"<tr>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {project.consultant.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.created_by.team.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.client} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.lead.vendor_company.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.created_by.employee_name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {project.start_date.strftime('%m/%d/%Y')} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {submission.employer} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;'> {project.city} </td>" \
                        f"</tr>\n"

            data = {
                "title": "Project Joining in this Week &#128221;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            post_msg_using_webhook(config.joined_url, data)
            post_msg_using_webhook(config.general_url, data)
            job.last_status = 'complete'
        except Exception as error:
            job.last_status = 'failed'
            print(error)

        finally:
            job.save()
