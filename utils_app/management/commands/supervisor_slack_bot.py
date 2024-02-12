from pytz import timezone
from datetime import datetime
from django.core.management import BaseCommand

from marketing.models import Interview
from log1.utils import send_personalized_message
from marketing.utils import create_sup_message_slack_payload
from utils_app.slack_notification import MessageCard as slack
from utils_app.utils import create_cron_error, create_cron_object, get_slack_id


class Command(BaseCommand):
    help = "This command is for posting scheduled and rescheduled interviews to supervisor's slack"

    def handle(self, *args, **options):
        job = create_cron_object(name='supervisor_slack_bot')
        try:
            slack_data = {}
            tz = timezone('EST')
            today_date = tz.localize(datetime.now())
            screening_types = (
                ('interview', 'Interview'),
                ('ip_screening', 'IP Screening'),
                ('vendor_screening', 'Vendor Tech Screening')
            )
            interviews = Interview.objects.filter(
                start_time__date=today_date, status__in=['scheduled', 'rescheduled']).exclude(
                supervisor__employee_id=9999
            ).order_by('start_time')

            for screening_type in screening_types:
                interviews_type = interviews.filter(screening_type=screening_type[0])
                for index, interview in enumerate(interviews_type):
                    supervisor = interview.supervisor
                    if not slack_data.get(supervisor, None):
                        slack_data[supervisor] = {}
                    if not slack_data.get(supervisor, {}).get(screening_type[1]):
                        slack_data[supervisor] = {screening_type[1]: []}
                    msg_payload = create_sup_message_slack_payload(interview, request=None)
                    if not msg_payload:
                        continue
                    slack_data[supervisor][screening_type[1]].append(msg_payload)

            for supervisor in slack_data.keys():
                payload = {
                    "data": slack_data.get(supervisor), "title": "Interviews Scheduled for today &#128203;"
                }
                if slack_data:
                    card_data, created = slack.daily_supervisor_interview(payload)
                    if not created:
                        create_cron_error(job, "Issue while creating slack card json personalized supervisor slack card")
                    member_id = supervisor.slack_id
                    if not member_id:
                        member_id = get_slack_id(supervisor)
                        if not member_id:
                            create_cron_error(
                                job,
                                f"member_id not found for user {supervisor.employee_name} with email {supervisor.email}"
                            )
                            continue

                    send_personalized_message(member_id, card_data.get('blocks'))
        except Exception as error:
            create_cron_error(job, error)
