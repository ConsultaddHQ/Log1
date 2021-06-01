from django.core.management import BaseCommand

from project.models import Project
from marketing.models import Submission
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    def handle(self, *args, **options):
        job = create_cron_object(name='complete_submissions')
        try:
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
        except Exception as error:
            create_cron_error(job, error)
