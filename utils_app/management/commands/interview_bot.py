import csv
from datetime import datetime

from django.core.management import BaseCommand

from constance import config
from log1.utils import write_info
from marketing.models import Interview
from utils_app.slack_notification import MessageCard as slack
from utils_app.utils import get_slack_tag, create_cron_error, create_cron_object, generate_s3_url


def create_csv_file(payload, report_name):
    """
    Generate a CSV file from the given payload and upload it to S3.
    """
    if not payload:
        return None

    try:
        filename = f"{report_name}_{datetime.now().strftime('%d-%B-%Y')}.csv"
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Consultant', 'Marketer', 'Supervisor', 'Screening Type', 'Type',
                'Round', 'Client', 'Vendor Company', 'Time', 'Job Title', 'Project Type'
            ])
            for screening_data in payload["screening_data"].values():
                for data in screening_data:
                    writer.writerow([
                        data.get('consultant'), data.get('marketer'), data.get('ctb_name'),
                        data.get('screening_type'), data.get('type'), data.get('round'),
                        data.get('client'), data.get('vendor'), data.get('start'),
                        data.get('position'), data.get('project_type')
                    ])
        return generate_s3_url(filename)
    except Exception as error:
        write_info(message=f"Error generating CSV: {error}", function='create_csv_file')
        return None


class Command(BaseCommand):
    help = "Post scheduled and rescheduled interviews on Slack channels."

    @staticmethod
    def get_slack_message_card_data(interview):
        """
        Prepare the data payload for an individual interview.
        """
        position = (interview.submission.lead.position.display_name
                    if interview.submission.lead.position else interview.submission.lead.job_title)
        supervisor = interview.supervisor
        call_type = interview.call_type.display_name if interview.call_type else "NA"

        return {
            "marketer": interview.marketer.employee_name,
            "type": interview.get_interview_mode_display(),
            "screening_type": interview.get_screening_type_display(),
            "client": interview.submission.client, "position": position,
            "project_type": interview.submission.get_work_type_display(),
            "start": interview.start_time.strftime('%m/%d/%Y::%I:%M %p EST'),
            "call_type": "otter.ai" if call_type == "Otter Al" else call_type,
            "round": interview.round, "consultant": interview.consultant.name,
            "ctb": get_slack_tag(supervisor), "ctb_name": supervisor.employee_name,
            "vendor": interview.submission.vendor.name if interview.submission.vendor else "NA",
        }

    @staticmethod
    def post_msg_to_slack(data, region):
        """
        Post interview data to the respective Slack channel.
        """
        file_url = create_csv_file(data, "interview_scheduled")
        payload = {
            "file_url": file_url, "title": f"{region} Interviews Scheduled for today",
            "screening_count": data.get("screening_count"), "data": data["screening_data"]
        }
        url = config.slack_usa_interview_update_url
        res, msg = slack.interview_data_report(payload, url)
        if msg == 'error':
            raise Exception(res)
        return res, msg

    def handle(self, *args, **options):
        job = create_cron_object(name='interview_bot')
        try:
            from pytz import timezone
            tz = timezone('EST')
            today_date = tz.localize(datetime.today())
            month_start_date = today_date.replace(day=1)

            screening_types = {
                'interview': 'Interview',
                'ip_screening': 'IP Screening',
                'vendor_screening': 'Vendor Screening'
            }
            interviews = Interview.objects.filter(
                start_time__date=today_date,
                status__in=['scheduled', 'rescheduled']
            ).order_by('start_time')

            us_slack_data = {"screening_count": {}, "screening_data": {}}

            for screening_type, screening_label in screening_types.items():
                interviews_type = interviews.filter(screening_type=screening_type)

                for interview in interviews_type:
                    slack_data = self.get_slack_message_card_data(interview)
                    if screening_label not in us_slack_data["screening_data"]:
                        us_slack_data["screening_data"][screening_label] = []
                    us_slack_data["screening_data"][screening_label].append(slack_data)

            screening_label = "Interview"
            screening_count = Interview.objects.filter(
                start_time__date__range=(month_start_date, today_date), screening_type__iexact=screening_label
            ).exclude(status="cancelled").values("submission_id").distinct().count()

            us_slack_data["screening_count"][screening_label] = screening_count

            try:
                self.post_msg_to_slack(us_slack_data, 'USA')
            except Exception as error:
                create_cron_error(job, error)

        except Exception as error:
            create_cron_error(job, error)
