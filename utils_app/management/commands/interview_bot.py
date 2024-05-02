import csv
from datetime import datetime
from django.core.management import BaseCommand

from constance import config

from log1.utils import write_info
from marketing.models import Interview
from utils_app.slack_notification import MessageCard as slack
from utils_app.utils import create_cron_error, create_cron_object, generate_s3_url


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

    @staticmethod
    def get_slack_message_card_data(interview):
        position = interview.submission.lead.position.display_name \
            if interview.submission.lead.position else interview.submission.lead.job_title
        supervisor = interview.supervisor
        call_type = interview.call_type.display_name if interview.call_type else "NA"

        return {
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

    # noinspection PyTypeChecker
    def handle(self, *args, **options):
        job = create_cron_object(name='interview_bot')
        try:
            from pytz import timezone
            us_slack_data = {}
            cn_slack_data = {}
            tz = timezone('EST')
            today_date = tz.localize(datetime.now())
            screening_types = (
                ('interview', 'Interview'),
                ('ip_screening', 'IP Screening'),
                ('vendor_screening', 'Vendor Tech Screening')
            )
            interviews = Interview.objects.filter(
                start_time__date=today_date, status__in=['scheduled', 'rescheduled']
            ).order_by('start_time')

            for screening_type in screening_types:
                interviews_type = interviews.filter(screening_type=screening_type[0])
                for index, interview in enumerate(interviews_type):
                    if index == 0:
                        if interview.submission.marketing_team == 'Consultadd Canada':
                            cn_slack_data[screening_type[1]] = []
                        else:
                            us_slack_data[screening_type[1]] = []

                    if interview.submission.marketing_team == 'Consultadd Canada':
                        if screening_type[1] not in cn_slack_data.keys():
                            cn_slack_data[screening_type[1]] = []
                        cn_slack_data[screening_type[1]].append(self.get_slack_message_card_data(interview))
                    else:
                        if screening_type[1] not in us_slack_data.keys():
                            us_slack_data[screening_type[1]] = []
                        us_slack_data[screening_type[1]].append(self.get_slack_message_card_data(interview))

            if us_slack_data:
                payload = {
                    "data": us_slack_data, "title": "USA Interviews Scheduled for today &#128203;",
                    'file_url': self.create_csv_file(us_slack_data, "interview_scheduled")
                }
                res, msg = slack.interview_data_report(payload, config.slack_usa_interview_update_url)
                if msg == 'error':
                    raise Exception(res)

            if cn_slack_data:
                payload = {
                    "data": cn_slack_data, "title": "Canada Interviews Scheduled for today &#128203;",
                    'file_url': self.create_csv_file(cn_slack_data, "interview_scheduled")
                }
                res, msg = slack.interview_data_report(payload, config.slack_canada_interview_update_url)
                if msg == 'error':
                    raise Exception(res)
        except Exception as error:
            create_cron_error(job, error)
