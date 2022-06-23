import csv
from datetime import date, datetime
from django.core.management import BaseCommand

from marketing.models import Interview
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):
    help = "This command is for sending Submission's Email to respective Consultants"

    def handle(self, *args, **options):
        job = create_cron_object(name='MayCallData')
        try:
            file = open('MayCallData.csv', 'w')
            writer = csv.writer(file)
            writer.writerow(['SupervisorName', 'Offer', 'Next Round', 'NR-Conversation', 'Failed', 'Failed-Conversation',
                             'Feedback_due', 'Feedback_due Conversation', 'Total'])
            interviews = Interview.objects.filter(start_time__gte=datetime(2022, 5, 1, 0, 0, 0), start_time__lt=datetime(2022, 6, 1, 0, 0, 0)).order_by(
                "supervisor_id").distinct("supervisor_id")
            supervisors = [interview.supervisor for interview in interviews]
            for sup in supervisors:
                obj = Interview.objects.filter(supervisor=sup, start_time__gte=datetime(2022, 5, 1, 0, 0, 0), start_time__lt=datetime(2022, 6, 1, 0, 0, 0))
                offer = obj.filter(status='offer').count()
                failed = obj.filter(status='failed').count()
                next_round = obj.filter(status='next_round').count()
                feedback_due = obj.filter(status='feedback_due').count()
                total = offer+feedback_due+failed+next_round
                writer.writerow(
                    [sup.employee_name, offer, next_round, ((offer+next_round)/total)*100, failed, (failed/total)*100, feedback_due, (feedback_due/total)*100, total
                    ]
                )
        except Exception as error:
            create_cron_error(job, error)
