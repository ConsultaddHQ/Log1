import os
from datetime import date
from datetime import timedelta
from django.conf import settings
from django.core.management import BaseCommand

import pandas as pd

from project.models import Project
from employee.models import User, Team
from marketing.models import Interview
from utils_app.mailing import send_email_attachment_multiple
from utils_app.utils import create_cron_error, create_cron_object


def mail_to_scrum(yesterday, this_week, scrum_masters, team_name, path, offers):
    try:
        path = [path]
        mail_data = {
            'to': scrum_masters, 'cc': [], 'bcc': [],
            'subject': 'Scrum Report of {} from {} to {}'.format(team_name, this_week, yesterday),
            'template': '../templates/scrum_report.html',
            'context': {
                'end': yesterday,
                'offers': offers,
                'team': team_name,
                'start': this_week,
            },
            'attachments': path
        }
        res, msg = send_email_attachment_multiple(mail_data, 'Log1@consultadd.com')
        if not msg:
            return res, "error"
        return res, "ok"
    except Exception as error:
        return error, "error"


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for Scrum Meeting report (Marketer's weekly Interviews)"

    # A command must define handle()
    def handle(self, *args, **options):
        job = create_cron_object(name='scrum_report')
        try:
            teams = Team.objects.filter(dept='Marketing')
            for team in teams:
                today = date.today()
                this_week = today - timedelta(days=7)
                queryset = list(Interview.objects.filter(
                    start_time__gte=this_week,
                    submission__created_by__team=team
                ).values_list('submission__created_by__employee_name', 'supervisor__employee_name', 'round',
                              'start_time', 'end_time', 'interview_mode', 'status', 'feedback'))
                df = pd.DataFrame.from_records(queryset, columns=['Marketer', 'CTB', 'Start Time', 'End Time', 'Round',
                                                                  'Type', 'Status', 'Feedback'])
                path = "{}/media/Scrum Report {} {}.csv".format(settings.BASE_DIR, team.name, str(today))
                df.to_csv(path, sep=',')
                scrum_masters = list(
                    User.objects.filter(team=team, role__name__in=['admin', 'proxy']).values_list('email', flat=True)
                )
                offers = Project.objects.filter(created__gte=today.replace(day=1), submission__created_by__team=team)
                yesterday = today - timedelta(days=1)
                mail_to_scrum(yesterday, this_week, scrum_masters, team.name, path, offers)
                if os.path.exists(path):
                    os.remove(path)
        except Exception as error:
            create_cron_error(job, error)
