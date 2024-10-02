import os
import csv
from datetime import datetime

from django.core.management import BaseCommand

from marketing.models import Interview
from utils_app.utils import generate_s3_url
from utils_app.slack_notification import MessageCard as slack


def get_interviewers_details(obj):
    """Retrieve interviewers details including name, email, and LinkedIn."""
    details = [
        {
            "name": interviewer.name,
            "email": interviewer.email,
            "linkedin": interviewer.linkedin
        }
        for interviewer in obj.interviewers.all()
    ]
    return details


def get_csv_file_url(slack_data):
    """Generate a CSV file for interview data and return its S3 URL."""
    header = [
        'Screening Type', 'Client', 'Total Rounds', 'Vendor', 'Position',
        'Consultant', 'Start Date', 'End Date', 'Interviewers'
    ]

    file_name = f"TechTrustInterviewReport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        with open(f"{file_name}", mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()

            # Writing data rows
            for interview_type, interviews in slack_data.items():
                for interview in interviews:
                    interviewer_info_text = str()
                    for interviewer in interview['interviewers']:
                        name = interviewer.get('name', '')
                        email = f"[{interviewer.get('email')}] " if interviewer.get('email') else ""
                        linkedin = f"HYPERLINK(\"{interviewer['linkedin']}\", \"LinkedIn Profile\"))" \
                            if interviewer.get('linkedin') else ""
                        interviewer_info_text += f"{name} {email}{linkedin}\n"

                    writer.writerow({
                        'Screening Type': interview_type, 'Client': interview['client'],
                        'Total Rounds': interview['total_rounds'], 'Vendor': interview['vendor'],
                        'Position': interview['position'], 'Consultant': interview['consultant'],
                        'Start Date': interview['start_date'], 'End Date': interview['end_time'],
                        'Interviewers': interviewer_info_text
                    })

        # Generate and return the S3 URL for the CSV file
        print(file_name)
        return generate_s3_url(file_name)
    except Exception as e:
        # Log the exception if CSV generation fails
        print(f"Error creating CSV file: {e}")
        return None


class Command(BaseCommand):

    @staticmethod
    def get_slack_message_card_data(interview):
        """Construct a dictionary with the necessary data for Slack message card."""
        try:
            # Extract interview details, handling nullable fields
            position = interview.submission.lead.position.display_name \
                if interview.submission.lead.position else interview.submission.lead.job_title
            return {
                "total_rounds": interview.submission.screening.order_by('round').first().round,
                "interviewers": get_interviewers_details(interview),
                "type": interview.get_screening_type_display(),
                "vendor": interview.submission.vendor.name,
                "position": position,
                "consultant": interview.consultant.name,
                "start_date": interview.start_time,
                "end_time": interview.end_time,
                "client": interview.submission.client
            }
        except Exception as e:
            print(f"Error fetching interview data: {e}")
            return {}

    def handle(self, *args, **options):
        slack_data = {}
        try:
            from pytz import timezone
            tz = timezone('EST')
            today_date = tz.localize(datetime.now()).date()

            # Define the screening types we are processing
            screening_types = [
                ('interview', 'Interview'),
                ('ip_screening', 'IP Screening'),
                ('vendor_screening', 'Vendor Tech Screening')
            ]

            # Query to fetch interviews scheduled for today (customize date for dynamic filtering)
            # interviews = Interview.objects.filter(start_time__date=today_date, status__in=['scheduled', 'rescheduled']).order_by('start_time')
            interviews = Interview.objects.filter(start_time__date="2024-08-01").order_by('start_time')

            # Iterate over each screening type and extract interviews
            for screening_type_key, screening_type_value in screening_types:
                interviews_by_type = interviews.filter(screening_type=screening_type_key)
                if interviews_by_type.exists():
                    slack_data[screening_type_value] = [
                        self.get_slack_message_card_data(interview) for interview in interviews_by_type
                    ]

            # Generate CSV URL
            csv_url = get_csv_file_url(slack_data)

            slack.tech_trust_customized_interview_update({
                "data": slack_data, "title": "Interview Report", "csv_url": csv_url
            })
        except Exception as error:
            print(f"Error during handle execution: {error}")
