from datetime import date, datetime
from django.core.management import BaseCommand

from constance import config
from utils_app.models import CronJob
from log1.utils import post_msg_using_webhook
from consultant.models import ConsultantMarketing


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for posting your payload to MatterMost app"

    # A command must define handle()
    def handle(self, *args, **options):
        job = CronJob.objects.get(name='pool_candidates')
        job.last_triggered_at = datetime.now()
        try:
            in_pool_con = ConsultantMarketing.objects.filter(
                in_pool=True,
                status='open'
            ).order_by('consultant_id', '-start').distinct('consultant_id')

            count = 1
            text = f"""<tr>
                        <th style="padding:5px 8px 5px 8px;">#</th>
                        <th style="padding:5px 8px 5px 8px;">Consultant</th>
                        <th style="padding:5px 8px 5px 8px;">Team</th>
                        <th style="padding:5px 8px 5px 8px;">Days</th>
                        <th style="padding:5px 8px 5px 8px;">Recruiter</th>
                        <th style="padding:5px 8px 5px 8px;">Marketer</th>
                        <th style="padding:5px 8px 5px 8px;">Skills</th>
                        <th style="padding:5px 8px 5px 8px;">Open Offer</th>
                        </tr>"""
            total = in_pool_con.count()

            for con in in_pool_con:
                if con.consultant.status != 'archived':
                    days, marketer, recruiter, open_offer = None, None, None, "NO"
                    team = ", ".join(con.teams.all().values_list('name', flat=True))
                    if con.start:
                        days = (date.today() - con.start).days
                    if con.primary_marketer:
                        marketer = con.primary_marketer.employee_name
                    if con.recruiter:
                        recruiter = con.consultant.recruiter.employee_name
                    open_offer_count = con.consultant.projects.filter(
                        statuses__is_current=True, statuses__status__in=['on_boarding', 'received']
                    ).count()
                    count += 1

                    text += f"""<tr>
<td style="padding:5px 8px 5px 8px;text-align: center;">{count}</td>
<td style="padding:5px 8px 5px 8px;">{con.consultant.name}</td>
<td style="padding:5px 8px 5px 8px;">{team}</td>
<td style="padding:5px 8px 5px 8px;text-align: center;">{days}</td>
<td style="padding:5px 8px 5px 8px;">{recruiter}</td>
<td style="padding:5px 8px 5px 8px;"> {marketer}</td>
<td style="padding:5px 8px 5px 8px;">{con.consultant.skills}</td>
<td style="padding:5px 8px 5px 8px;text-align: center;">{open_offer_count}</td>
</tr>\n"""

                    if count % 35 == 0:
                        data = {
                            "title": "Pool Candidates &#127958;",
                            "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
                        }

                        post_msg_using_webhook(config.pool_channel_url, data)
                        text = f"""<tr>
                                    <th style="padding:5px 8px 5px 8px;">#</th>
                                    <th style="padding:5px 8px 5px 8px;">Consultant</th>
                                    <th style="padding:5px 8px 5px 8px;">Team</th>
                                    <th style="padding:5px 8px 5px 8px;">Days</th>
                                    <th style="padding:5px 8px 5px 8px;">Recruiter</th>
                                    <th style="padding:5px 8px 5px 8px;">Marketer</th>
                                    <th style="padding:5px 8px 5px 8px;">Skills</th>
                                    <th style="padding:5px 8px 5px 8px;">Open Offer</th>
                                    </tr>"""
            data = {
                "title": "Pool Candidates &#127958;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }

            post_msg_using_webhook(config.pool_channel_url, data)
            job.last_status = 'complete'
        except Exception as error:
            job.last_status = 'failed'
            print(error)

        finally:
            job.save()
