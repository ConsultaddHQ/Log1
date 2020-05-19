from datetime import datetime, timedelta, date
from django.core.management import BaseCommand

from constance import config

from employee.models import User
from marketing.models import Submission
from consultant.models import Consultant
from utils_app.mailing import send_email


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for sending Submission's Email to respective Consultants"

    # A command must define handle()
    def handle(self, *args, **options):
        consultants = Consultant.objects.filter(marketing__status='open').exclude(status='archived').distinct()
        submission_data = []
        today = datetime.today()
        if today.weekday() == 0:
            days = 3
            last_2_days = today - timedelta(days=5)
        else:
            days = 2
            last_2_days = today - timedelta(days=2)
        for consultant in consultants:
            submission_ids = []
            scrum_masters = []
            queryset = Submission.objects.filter(consultant_marketing__consultant=consultant, created__gte=last_2_days)
            submissions = []
            if not queryset:
                continue
            count = 1
            for submission in queryset:
                submissions.append(
                    {
                        "no": count,
                        "location": submission.lead.city,
                        "job_title": submission.lead.job_title,
                        "skill": submission.lead.primary_skill,
                        "job_desc": submission.lead.job_desc.replace("\n", " ;newline; "),
                    }
                )
                count += 1
                users = User.objects.filter(team=submission.created_by.team, role__name__in=['admin', 'proxy'])
                for user in users:
                    scrum_masters.append(user.email)
                submission_ids.append(submission.id)
            cc = list(set(scrum_masters))
            mail_data = {
                'bcc': [],
                'to': [consultant.email],
                'cc': cc + [config.RELATIONS, config.RECRUITMENT],
                'subject': '{} - Submissions - {}'.format(consultant.name, str(date.today())),
                'template': '../templates/consultants_submissions.html',
                'context': {
                    'consultant': consultant.name,
                    'submissions': submissions,
                    'days': days,
                },
            }
            submission_data.append({
                "scrum_masters": cc,
                "consultant": consultant.id,
                "submissions": submission_ids,
                "consultant_name": consultant.name,
                "consultant_email": consultant.email,

            })
            reply_to = [config.RELATIONS]
            send_email(mail_data, "log1@consultadd.com", reply_to)

        mail_data = {
            'cc': [],
            'bcc': [],
            'to': ['sarang.m@consultadd.com'],
            'subject': f"Consultant submission data {str(last_2_days)} - {str(date.today())}",
            'template': '../templates/consultants_submissions_admin_report.html',
            'context': {
                "data": submission_data,
                'days': days,
            },
        }
        send_email(mail_data, "log1@consultadd.com")

