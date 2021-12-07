from datetime import date
from django.core.management import BaseCommand

from constance import config
from log1.utils import post_msg_using_webhook
from consultant.models import ConsultantMarketing
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting pool candidates on channel"

    def handle(self, *args, **options):
        job = create_cron_object(name='pool_candidates')
        try:
            count = 1
            in_pool_con = ConsultantMarketing.objects.filter(
                in_pool=True,
                status='open'
            ).order_by('consultant_id', '-start').distinct('consultant_id')

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

            for con in in_pool_con:
                if con.consultant.status != 'terminated':
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

                        res2, msg2 = post_msg_using_webhook(config.pool_channel_url, data)
                        if msg2 == 'error':
                            create_cron_error(job, res2)
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

                    count += 1
            data = {
                "title": "Pool Candidates &#127958;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }

            res, msg = post_msg_using_webhook(config.pool_channel_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
