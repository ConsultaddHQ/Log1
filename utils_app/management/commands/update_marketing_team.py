from employee.models import Team
from django.core.management import BaseCommand

from project.models import Project
from utils_app.models import Choice, ContentType


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            team_cn = Team.objects.get(name='Consultadd Canada')
            po_qs = Project.objects.filter(id__in=[1265, 1300, 1404])
            for obj in po_qs:
                obj.submission.marketing_team = team_cn
                obj.submission.save()
                print(f"https://log1.com/#/details/{obj.submission_id}/project?id={obj.id}")
        except Exception as error:
            print(error)
