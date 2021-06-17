from django.core.management import BaseCommand

from project.models import Project
from marketing.models import Submission
from utils_app.utils import create_cron_error, create_cron_object


class Command(BaseCommand):

    def handle(self, *args, **options):
        job = create_cron_object(name='complete_submissions')
        try:
            subs = Submission.objects.filter(is_complete=False)
            for submission in subs:
                if submission.rate and submission.vendor and submission.client and \
                        (submission.lead.job_desc and len(submission.lead.job_desc) > 20):
                    submission.is_complete = True
                    submission.save()

        except Exception as error:
            create_cron_error(job, error)
