from datetime import datetime
from django.core.management import BaseCommand

from constance import config
from marketing.models import Interview
from log1.utils import post_msg_using_webhook
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for posting scheduled and rescheduled interviews on channel"

    def handle(self, *args, **options):
        job = create_cron_object(name='interview_bot')
        try:
            from pytz import timezone
            tz = timezone('EST')
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

            for index, interview in enumerate(interviews):
                position = interview.submission.lead.position.display_name
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

            data = {
                "title": "Interviews Scheduled for today &#128203;",
                "text": f"""<table border='2' style='border-collapse:collapse'>{text}</table>"""
            }
            res, msg = post_msg_using_webhook(config.announcement_url, data)
            if msg == 'error':
                raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
