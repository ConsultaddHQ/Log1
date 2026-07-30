import csv
from datetime import datetime, timedelta, date
from django.core.management import BaseCommand

from marketing.models import Submission
from utils_app.thred_mail import send_email_attachment_multiple
from utils_app.utils import create_cron_error, create_cron_object, delete_temp_file


class Command(BaseCommand):
    help = "This command is for sending incomplete submission notification"

    def handle(self, *args, **options):
        job = create_cron_object(name='incomplete_submissions')
        try:
            data = []
            today = datetime.today()
            if today.weekday() == 0:
                days = 3
                last_2_days = today - timedelta(days=5)
            else:
                days = 2
                last_2_days = today - timedelta(days=2)
            subs = Submission.objects.filter(is_complete=False, created__gte=last_2_days).order_by('marketing_team__name')
            if not subs:
                exit()

            col_name = ["Submission ID", "Consultant Name", "Marketer", "Recruiter", "Marketing Team", "Client",
                        "Vendor", "App Link"]
            file = open(f"incomplete_submission.csv", 'w+')
            writer = csv.writer(file)
            writer.writerow(col_name)

            for submission in subs:
                submission_data = {
                    "client": submission.client,
                    "submission_id": submission.id,
                    "vendor": submission.vendor.name,
                    "consultant_name": submission.consultant.name,
                    "marketer": submission.created_by.employee_name,
                    "marketing_team": submission.marketing_team.name,
                    "recruiter": submission.consultant.recruiter.employee_name if submission.consultant.recruiter else 'NA',
                    "app_link": f"https://app.log1.com/#/details/{submission.id}/submission"
                }
                writer.writerow([
                    submission_data['submission_id'], submission_data['consultant_name'], submission_data['marketer'],
                    submission_data['recruiter'], submission_data['marketing_team'], submission_data['client'],
                    submission_data['vendor'], submission_data['app_link']
                ])
                data.append(submission_data)

            mail_data = {
                'bcc': ['shreyas.k@consultadd.com'],
                'cc': [], 'attachments': [f'{file.name}'],
                'to': ['marketing@consultadd.com', 'recruitment@consultadd.com'],
                'subject': f"Consultant incomplete submission data {str(last_2_days.strftime('%m/%d/%Y'))} -"
                           f" {str(date.today().strftime('%m/%d/%Y'))}",
                'template': '../templates/incomplete_submission.html',
                'context': {
                    'days': days,
                    "data": data,
                    'start': str(last_2_days.strftime('%m/%d/%Y')),
                    'end': str(date.today().strftime('%m/%d/%Y')),
                },
            }
            send_email_attachment_multiple(mail_data, 'product@consultadd.com', None, None, None, True)
            delete_temp_file([file.name])
        except Exception as error:
            create_cron_error(job, error)
