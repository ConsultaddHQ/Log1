from datetime import date, timedelta
from django.core.management import BaseCommand

from constance import config
from project.models import Project
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting Projects joining in this week"

    def handle(self, *args, **options):
        job = create_cron_object(name='monday_po_alert')
        try:
            end = date.today() - timedelta(days=1)
            start = date.today() - timedelta(days=7)

            text = f"<tr>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Consultant</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Team</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Client</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Vendor</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Marketer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Start Date</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Employer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>City</th>" \
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
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.marketing_team.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.client} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.lead.vendor_company.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.created_by.employee_name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {project.start_date.strftime('%m/%d/%Y')} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.employer} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {project.city} </td>" \
                        f"</tr>\n"

            data = {
                "title": "Project Joined Last Week &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
            }
            payload = {
                "data": data, "title": data.get('title'),
                "report_name": "monday_po_alert",
            }
            # MessageCard.data_report(payload, config.slack_usa_joining_termination)

            text = f"<tr>" \
                   f"<th style='padding:2px 8px 0px 8px;'>Consultant</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Team</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Client</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Vendor</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Marketer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Start Date</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>Employer</th>" \
                   f"<th style='padding:5px 8px 5px 8px;font-size: 2.5em;'>City</th>" \
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
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {project.consultant.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.marketing_team.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.client} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.lead.vendor_company.name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.created_by.employee_name} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {project.start_date.strftime('%m/%d/%Y')} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {submission.employer} </td>" \
                        f"<td style='padding:5px 8px 5px 8px;font-size: 2.5em;'> {project.city} </td>" \
                        f"</tr>\n"

            data = {
                "title": "Project Joining in this Week &#128221;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
            }
            payload = {
                "data": data, "title": data.get('title'),
                "report_name": "monday_po_alert",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_usa_joining_termination)
            # if msg == 'error':
            #     create_cron_error(job, res)
            payload = {
                "data": data, "title": data.get('title'),
                "report_name": "monday_po_alert",
            }
            # res, msg = MessageCard.data_report(payload, config.slack_general_url)
            # if msg == 'error':
            #     create_cron_error(job, res)

        except Exception as error:
            create_cron_error(job, error)
