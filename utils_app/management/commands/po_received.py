from datetime import datetime, date
from django.core.management import BaseCommand

from project.models import Project
from project.utils import ProjectUtil
from utils_app.slack_notification import MessageCard as slack

project = Project.objects.get(id=1706)


def diff_month_days(start, end):
    if type(start) == str:
        start = datetime.strptime(str(start), '%Y-%m-%d')
    if type(end) == str:
        end = datetime.strptime(str(end), '%Y-%m-%d')
    return (end.year - start.year) * 12 + end.month - start.month


class Command(BaseCommand):

    # def fetch_project_termination_count(self):
    #     try:
    #         team = project.submission.marketing_team
    #         day_one = datetime.today().replace(day=1, hour=0, minute=0)
    #         total_count = Project.objects.filter(
    #             statuses__status__istartswith="terminated", statuses__created__gte=day_one
    #         ).count()
    #         team_count = Project.objects.filter(
    #             statuses__created__gte=day_one,
    #             submission__marketing_team=team,
    #             statuses__status__istartswith="terminated"
    #         ).count()
    #         return total_count, team_count, team.name
    #     except Exception as error:
    #         print(str(error))

    def handle(self, *args, **options):
        try:
            po_obj = ProjectUtil(project)
            po_obj.send_receive_notification()
        except Exception as error:
            print(error)
