import csv
from datetime import datetime
from django.core.management import BaseCommand

from constance import config

from log1.utils import write_info, send_personalized_message
from marketing.models import Interview
from utils_app.slack_notification import MessageCard as slack
from utils_app.utils import create_cron_error, create_cron_object, generate_s3_url, get_slack_id


class Command(BaseCommand):
    help = "This command is for posting scheduled and rescheduled interviews on channel"

    @staticmethod
    def create_csv_file(payload, report_name):
        try:
            filename = f"{report_name}_{datetime.now().strftime('%d-%B-%Y')}"
            file = open(f'{filename}.csv', 'w')
            writer = csv.writer(file)
            writer.writerow(['Consultant', 'Marketer', 'Supervisor', 'Screening Type', 'Type',
                             'Round', 'Client', 'Time', 'Job Title', 'Project Type'])
            for key in payload.keys():
                for data in payload[key]:
                    writer.writerow([
                        data.get('consultant'), data.get('marketer'), data.get('ctb_name'), data.get('screening_type'),
                        data.get('type'), data.get('round'), data.get('client'), data.get('start'), data.get('position'),
                        data.get('project_type')
                    ])
            file.close()
            file_url = generate_s3_url(file.name)
            return file_url
        except Exception as error:
            write_info(message=f"{error}", function='create_csv_file')
            return "file_url"

    # noinspection PyTypeChecker
    def handle(self, *args, **options):
        job = create_cron_object(name='interview_bot')
        try:
            from pytz import timezone
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
                    position = interview.submission.lead.position.display_name \
                        if interview.submission.lead.position else interview.submission.lead.job_title
                    call_type = interview.call_type.display_name if interview.call_type else "NA"
                    slack_data[supervisor][screening_type[1]].append(
                        {
                            "type": interview.get_interview_mode_display(),
                            "screening_type": interview.get_screening_type_display(),
                            "project_type": interview.submission.get_work_type_display(),
                            "round": interview.round, "ctb_name": supervisor.employee_name,
                            "start": interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST'),
                            "call_type": "otter.ai" if call_type == "Otter Al" else call_type,
                            "marketer": interview.marketer.employee_name, "position": position,
                            "consultant": interview.consultant.name, "client": interview.submission.client,
                            "ctb": f'<@{supervisor.slack_id}>' if supervisor.slack_id else supervisor.employee_name
                        }
                    )

            for supervisor in slack_data.keys():
                payload = {
                    'file_url': self.create_csv_file(slack_data.get(supervisor), "interview_scheduled"),
                    "data": slack_data.get(supervisor), "title": "Interviews Scheduled for today &#128203;"
                }
                if slack_data:
                    card_data = slack.personlized_interview_data_report(payload, config.slack_announcement_url)
                    member_id = supervisor.slack_id
                    if not member_id:
                        member_id = get_slack_id(supervisor)
                        if not member_id:
                            # create_cron_error(
                            #     job,
                            #     f"member_id not found for user {supervisor.employee_name} with email {supervisor.email}"
                            # )
                            print("member_id not found")
                            continue
                    breakpoint()
                    send_personalized_message(member_id, card_data.get('blocks'))
        except Exception as error:
            print(error)