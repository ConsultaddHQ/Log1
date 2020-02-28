import os
import logging
from datetime import date
from datetime import timedelta
from django.conf import settings
from django.core.management import BaseCommand

from project.models import Project
from employee.models import User, Team
from marketing.models import Screening
from utils_app.mailing import send_email_attachment_multiple

import pandas as pd

logger = logging.getLogger(__name__)


def mail_to_scrum(yesterday, this_week, scrum_master, path, offers):
    try:
        path = [path]
        to = [scrum_master.email]
        mail_data = {
            'to': to,
            'cc': [],
            'bcc': [],
            'subject': 'Scrum Report of {} from {} to {}'.format(scrum_master.team.name, this_week, yesterday),
            'template': '../templates/scrum_report.html',
            'context': {
                'end': yesterday,
                'offers': offers,
                'start': this_week,
                'team': scrum_master.team.name,
            },
            'attachments': path
        }
        res = send_email_attachment_multiple(mail_data, 'Log1')
        logger.error("Weekly Report mail res for {}: {}".format(scrum_master.email, res))
        return res, "ok"
    except Exception as error:
        logger.error("Weekly Report mail exception error for {}: {}".format(scrum_master.email, error))
        return error, "error"


class Command(BaseCommand):
    # Show this when the user types help
    help = "this command is for Scrum Meeting report (Marketer's weekly Interviews)"

    # A command must define handle()
    def handle(self, *args, **options):
        teams = Team.objects.filter(dept='Marketing')
        for team in teams:
            today = date.today()
            this_week = today - timedelta(days=7)
            queryset = list(Screening.objects.filter(
                start_time__gte=this_week,
                submission__lead__marketer__team=team
            ).values_list('submission__lead__marketer__full_name', 'ctb__full_name', 'start_time', 'round', 'type',
                          'status', 'feedback'))
            df = pd.DataFrame.from_records(queryset, columns=['Marketer', 'CTB', 'Start Time', 'Round', 'Type',
                                                              'Status', 'Feedback'])
            path = "{}/media/Scrum Report {} {}.xlsx".format(settings.BASE_DIR, team.name, str(today))
            writer = pd.ExcelWriter(path, engine='xlsxwriter', datetime_format='mm/dd/yy hh:mm:ss',
                                    options={'remove_timezone': True})

            df.to_excel(writer, sheet_name='Sheet1')
            writer.save()
            scrum_masters = User.objects.filter(team=team, role__name='admin')
            offers = Project.objects.filter(created__gte=today.replace(day=1), submission__lead__marketer__team=team)
            for user in scrum_masters:
                yesterday = today - timedelta(days=1)
                response, res = mail_to_scrum(yesterday, this_week, user, path, offers)
                if res == 'ok' and os.path.exists(path):
                    os.remove(path)

            if os.path.exists(path):
                os.remove(path)
