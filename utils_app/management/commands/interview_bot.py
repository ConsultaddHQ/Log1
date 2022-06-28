from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Interview
from utils_app.slack_notification import MessageCard as slack
from utils_app.teams_notification import MessageCard as teams
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting scheduled and rescheduled interviews on channel"

    def handle(self, *args, **options):
        job = create_cron_object(name='interview_bot')
        try:
            from pytz import timezone
            tz = timezone('EST')
            slack_data = []
            today_date = tz.localize(datetime.now())
            interviews = Interview.objects.filter(
                start_time__date=today_date,
                status__in=['scheduled', 'rescheduled', 'feedback_due'],
            ).order_by('start_time')

            text = f""" <tr>
                <th style="padding:5px 8px 5px 8px;">#</th>
                <th style="padding:5px 8px 5px 8px;">CTB</th>
                <th style="padding:5px 8px 5px 8px;">Round</th>
                <th style="padding:5px 8px 5px 8px;">Type</th>
                <th style="padding:5px 8px 5px 8px;">Start Time</th>
                <th style="padding:5px 8px 5px 8px;">Consultant</th>
                <th style="padding:5px 8px 5px 8px;">Client</th>
                <th style="padding:5px 8px 5px 8px;">Marketer</th>
                <th style="padding:5px 8px 5px 8px;">Job Position</th>
                </tr>"""

            for index, interview in enumerate(interviews[0: 7]):
                position = interview.submission.lead.position.display_name if interview.submission.lead.position else None
                text += f"""<tr>
                                <td style="padding:5px 8px 5px 8px;"> {index + 1} </td>
                                <td style="padding:5px 8px 5px 8px;"> {interview.supervisor.employee_name} </td>
                                <td style="padding:5px 8px 5px 8px; text-align: center;"> {interview.round} </td>
                                <td style="padding:5px 8px 5px 8px;"> {interview.get_interview_mode_display()} </td>
                                <td style="padding:5px 8px 5px 8px;"> 
                                        {interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST')} </td>
                                <td style="padding:5px 8px 5px 8px;"> {interview.consultant.name} </td>
                                <td style="padding:5px 8px 5px 8px;"> {interview.submission.client} </td>
                                <td style="padding:5px 8px 5px 8px;"> {interview.marketer.employee_name} </td>
                                <td style="padding:5px 8px 5px 8px;"> {position} </td>
                            </tr>"""
                slack_data.append(
                    {
                        "type": interview.get_interview_mode_display(),
                        "ctb": interview.supervisor.employee_name, "round": interview.round,
                        "start": interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST'),
                        "marketer": interview.marketer.employee_name, "position": position,
                        "consultant": interview.consultant.name, "client": interview.submission.client,
                    }
                )
            data = {
                "title": "Interviews Scheduled for today &#128203;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            payload = {
                "data": slack_data,
                "title": data.get('title'),
                "report_name": "interview_scheduled",
            }
            teams.data_report(data, config.announcement_url)
            res, msg = slack.data_report(payload, config.slack_announcement_url)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
