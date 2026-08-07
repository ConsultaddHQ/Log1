import csv
from pytz import timezone
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from marketing.models import Interview


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


def get_csv_file(slack_data):
    """Generate a CSV file for interview data and return its S3 URL."""
    header = [
        'Screening Type', 'Client', 'Total Rounds', 'Vendor', 'Position',
        'Consultant', 'Start Time', 'End Time', 'Job Location', 'Status', 'Interviewers'
    ]

    file_name = f"InterviewReport_{(datetime.now().date()-timedelta(days=1)).strftime('%Y-%m-%d')}.csv"
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
                        'Job Location': interview['job_location'], 'Status': interview['status'],
                        'Interviewers': interviewer_info_text
                    })

        # Generate and return the S3 URL for the CSV file
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
                "status": interview.get_status_display(),
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
            tz = timezone('EST')
            prev_date = tz.localize(datetime.now()).date() - timedelta(days=1)
            if prev_date.weekday() == 6:
                prev_date -= timedelta(days=2)

            # Query to fetch interviews scheduled for today (customize date for dynamic filtering)
            interview_qs = Interview.objects.filter(
                start_time__date__gte="2024-01-01", start_time__date__lt="2024-10-23", screening_type='interview'
            ).exclude(status='canceled').order_by('start_time')

            slack_data["Interview"] = [
                self.get_slack_message_card_data(interview) for interview in interview_qs
            ]

            # Generate CSV URL
            get_csv_file(slack_data)

        except Exception as error:
            print(f"Error during handle execution: {error}")
