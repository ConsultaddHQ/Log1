import csv
from django.core.management import BaseCommand

from project.models import ProjectAssociates, Project
from project.serializers import ProjectAssociatesSerializer
from project.utils import assign_project_associates


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            pa = Project.objects.get(id=1477)
            result = assign_project_associates(pa)
            print(result)
        except Exception as error:
            print(error)
