from django.core.management import BaseCommand

from dashboard.models import QuickActions
from legal.models import Petition
from marketing.models import Submission
from project.models import Project, TimeSheet, Leave, ConsultantLeave
from consultant.models import Consultant


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:

            old_consultant = Consultant.objects.get(id=853)
            new_consultant = Consultant.objects.get(id=1109)

            projects = Project.objects.filter(consultant=old_consultant)
            for project in projects:
                project.consultant = new_consultant
                project.save()

            petitions = Petition.objects.filter(beneficiary=old_consultant)
            for petition in petitions:
                petition.beneficiary = new_consultant
                petition.save()

            leaves = ConsultantLeave.objects.filter(consultant=old_consultant)
            for leave in leaves:
                leave.consultant = new_consultant
                leave.save()

            old_consultant.delete()
        except Exception as error:
            print(error)
