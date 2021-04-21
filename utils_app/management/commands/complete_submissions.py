from django.core.management import BaseCommand

from marketing.models import Submission
from project.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        subs = Submission.objects.all()
        for submission in subs:
            if submission.rate and submission.vendor and submission.client and submission.lead.job_desc:
                submission.is_complete = True
                submission.save()

        projects = Project.objects.all()
        for project in projects:
            project.rate = project.submission.rate
            project.employer = project.submission.employer
            project.save()
