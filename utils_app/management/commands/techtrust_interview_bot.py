import csv
from datetime import datetime
from django.core.management import BaseCommand

from marketing.models import Interview
from utils_app.slack_notification import MessageCard as slack


def get_interviewers_details(obj):
    details = list()
    interviewer_qs = obj.interviewers.all()
    for obj in interviewer_qs:
        details.append({
            "name": obj.name,
            "email": obj.email,
            "linkedin": obj.linkedin
        })
    return details

class Command(BaseCommand):

    @staticmethod
    def get_slack_message_card_data(interview):
        position = interview.submission.lead.position.display_name \
            if interview.submission.lead.position else interview.submission.lead.job_title
        return {
            "total_rounds": interview.submission.screening.filter().order_by('round').first().round,
            "interviewers": get_interviewers_details(interview), "consultant": interview.consultant.name,
            "vendor": interview.submission.vendor.name, "position": position, "client": interview.submission.client
        }

    def handle(self, *args, **options):
        slack_data = dict()
        try:
            from pytz import timezone
            tz = timezone('EST')
            today_date = tz.localize(datetime.now())
            screening_types = (
                ('interview', 'Interview'),
                ('ip_screening', 'IP Screening'),
                ('vendor_screening', 'Vendor Tech Screening')
            )
            # interviews = Interview.objects.filter(
            #     start_time__date=today_date, status__in=['scheduled', 'rescheduled']
            # ).order_by('start_time')
            interviews = Interview.objects.filter(start_time__date="2024-08-01").order_by('start_time')

            for screening_type in screening_types:
                interviews_type = interviews.filter(screening_type=screening_type[0])
                for index, interview in enumerate(interviews_type[0: 5]):
                    if index == 0:
                        slack_data[screening_type[1]] = []

                    if screening_type[1] not in slack_data.keys():
                        slack_data[screening_type[1]] = []
                    slack_data[screening_type[1]].append(self.get_slack_message_card_data(interview))

            res, msg = slack.techtrust_customized_interview_update({
                "data": slack_data, "title": "Interview report"
            })
        except Exception as error:
            print(error)
