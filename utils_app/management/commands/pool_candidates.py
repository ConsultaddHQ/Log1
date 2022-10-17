from datetime import date
from django.core.management import BaseCommand

from constance import config
from consultant.models import ConsultantMarketing
from utils_app.slack_notification import MessageCard
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting pool candidates on channel"

    def handle(self, *args, **options):
        job = create_cron_object(name='pool_candidates')
        try:
            count = 1
            slack_payload = []
            in_pool_con = ConsultantMarketing.objects.filter(
                in_pool=True,
                status='open'
            ).order_by('consultant_id', '-start').distinct('consultant_id')

            text = f"""<tr>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">#</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Consultant</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Team</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Days</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Recruiter</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Marketer</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Skills</th>
                        <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Open Offer</th>
                        </tr>"""

            for con in in_pool_con:
                if con.consultant.status != 'terminated':
                    days, marketer, recruiter, open_offer = None, None, None, "NO"
                    team = ", ".join(con.teams.all().values_list('name', flat=True))
                    if con.start:
                        days = (date.today() - con.start).days
                    if con.primary_marketer:
                        marketer = f'<@{con.primary_marketer.slack_id}>' \
                            if con.primary_marketer.slack_id else con.primary_marketer.employee_name
                    if con.recruiter:
                        recruiter = f'<@{con.consultant.recruiter.slack_id}>' \
                            if con.consultant.recruiter.slack_id else con.consultant.recruiter.employee_name
                    open_offer_count = con.consultant.projects.filter(
                        statuses__is_current=True, statuses__status__in=['on_boarding', 'received']
                    ).count()

                    text += f"""<tr>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{count}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{con.consultant.name}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{team}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{days}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{recruiter}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;"> {marketer}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;">{con.consultant.skills}</td>
<td style="padding:5px 8px 5px 8px;font-size: 2.5em;text-align: center;">{open_offer_count}</td>
</tr>\n"""
                    data = {
                        "consultant": con.consultant.name, "team": team, "days": days, "marketer": marketer,
                        "recruiter": recruiter, "skills": con.consultant.skills, "open_offer": open_offer_count
                    }
                    slack_payload.append(data)
                    # if count % 35 == 0:
                    #     data = {
                    #         "title": "Pool Candidates &#127958;",
                    #         "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
                    #     }
                    #
                    #     payload = {
                    #         "data": data, "title": data.get('title'), "report_name": job.name,
                    #     }
                    #     # res2, msg2 = MessageCard.data_report(payload, config.slack_pool_channel_url)
                    #     # if msg2 == 'error':
                    #     #     create_cron_error(job, res2)
                    #     text = f"""<tr>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">#</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Consultant</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Team</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Days</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Recruiter</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Marketer</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Skills</th>
                    #                 <th style="padding:5px 8px 5px 8px;font-size: 2.5em;">Open Offer</th>
                    #                 </tr>"""

                    count += 1
            data = {
                "title": "Pool Candidates &#127958;",
                "text": f"""<table border='5' style='border-collapse:collapse; width:99vw; height:99vh'>{text}</table>"""
            }

            payload = {"data": slack_payload, "report_name": job.name}
            res, msg = MessageCard.pool_candidate_report(payload, config.slack_pool_channel_url)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
