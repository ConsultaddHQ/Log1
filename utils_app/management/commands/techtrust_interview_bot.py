import os
import csv
from pytz import timezone
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from marketing.models import Interview
from utils_app.utils import generate_s3_url
from utils_app.slack_notification import MessageCard as slack


def get_prev_date(date_str=None):
    try:
        tz = timezone('EST')
        if date_str:
            input_date = datetime.strptime(date_str, '%Y-%m-%d')  # Parse the input date string
            input_date = tz.localize(input_date).date()  # Localize to EST and get the date
        else:
            input_date = tz.localize(datetime.now()).date()  # Use current date in EST if no date_str

        if input_date.weekday() == 0:  # Monday
            previous_date = input_date - timedelta(days=3)
        else:
            previous_date = input_date - timedelta(days=1)

        return previous_date
    except Exception as e:
        raise Exception


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
        'Consultant', 'Start Time', 'End Time', 'Job Location', 'Interviewers'
    ]

    file_name = f"TechTrustInterviewReport_{(datetime.now().date()-timedelta(days=1)).strftime('%Y-%m-%d')}.csv"
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
                        'Start Time': interview['start_time'], 'End Time': interview['end_time'],
                        'Job Location': interview['job_location'], 'Interviewers': interviewer_info_text
                    })

        # Generate and return the S3 URL for the CSV file
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
                "total_rounds": interview.round,
                "interviewers": get_interviewers_details(interview),
                "type": interview.get_screening_type_display(),
                "vendor": interview.submission.vendor.name,
                "position": position,
                "consultant": interview.consultant.name,
                "start_time": interview.start_time.strftime("%I:%M %p"),
                "end_time": interview.end_time.strftime("%I:%M %p"),
                "client": interview.submission.client,
                "job_location": interview.submission.lead.city
            }
        except Exception as e:
            print(f"Error fetching interview data: {e}")
            return {}

    def handle(self, *args, **options):
        slack_data = {}
        try:
            prev_date = get_prev_date()
            # Query to fetch interviews scheduled for today (customize date for dynamic filtering)
            interview_qs = Interview.objects.filter(
                start_time__date=prev_date, screening_type='interview'
            ).exclude(status='cancelled').order_by('start_time')

            # Iterate over each screening type and extract interviews
            # for screening_type_key, screening_type_value in screening_types:
            #     interviews_by_type = interviews.filter(screening_type=screening_type_key)
            #     if interviews_by_type.exists():
            #         slack_data[screening_type_value] = [
            #             self.get_slack_message_card_data(interview) for interview in interviews_by_type
            #         ]
            slack_data["Interview"] = [
                self.get_slack_message_card_data(interview) for interview in interview_qs
            ]

            # Generate CSV URL
            csv_url = get_csv_file_url(slack_data)

            slack.tech_trust_customized_interview_update({
                "data": slack_data, "title": "Interview Report", "csv_url": csv_url
            })
        except Exception as error:
            print(f"Error during handle execution: {error}")
