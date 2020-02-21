from datetime import datetime, timedelta, date
from django.core.management import BaseCommand

from constance import config
from marketing.models import Submission
from consultant.models import Consultant
from utils_app.mailing import send_email


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for sending Submission's Email to respective Consultants"

    # A command must define handle()
    def handle(self, *args, **options):
        consultants = Consultant.objects.filter(marketing__status='open')
        for consultant in consultants:
            today = datetime.today()
            if today.weekday() == 0:
                days = 3
                last_2_days = today - timedelta(days=4)
            else:
                days = 2
                last_2_days = today - timedelta(days=2)
            queryset = Submission.objects.filter(consultant_marketing__consultant=consultant, created__gte=last_2_days)
            submissions = []
            if not queryset:
                continue
            count = 1
            for submission in queryset:
                submissions.append(
                    {
                        "no": count,
                        "location": submission.lead.location,
                        "job_title": submission.lead.job_title,
                        "skill": submission.lead.primary_skill,
                        "job_desc": submission.lead.job_desc.replace("\n", " ;newline; "),
                    }
                )
                count += 1
            mail_data = {
                'bcc': [],
                # 'to': [consultant.email],
                'to': ['sarang.m@consultadd.in'],
                'cc': [config.RELATIONS, config.RECRUITMENT],
                'subject': '{} - Submissions - {}'.format(consultant.name, str(date.today())),
                'template': '../templates/consultants_submissions.html',
                'context': {
                    'consultant': consultant.name,
                    'submissions': submissions,
                    'days': days,
                },
            }
            reply_to = ['relations@consultadd.com']
            send_email(mail_data, "log1@consultadd.com", reply_to)

