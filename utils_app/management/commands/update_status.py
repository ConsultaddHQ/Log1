from django.core.management import BaseCommand

from utils_app.models import Choice
from marketing.models import Submission, Interview
from django.contrib.auth.models import ContentType
from utils_app.utils import create_cron_error, create_cron_object, get_timezone


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='assign_test_update')
        try:
            sub = Submission.objects.filter(created_by__id=1)
            for i in sub:
                i.status = 'archive'
                i.save()

            content_type = ContentType.objects.get(model='user')
            TECHNOLOGIES = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps',
                            'BA', 'DA', 'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce',
                            'Cyber Security']
            for tech in TECHNOLOGIES:
                Choice.objects.create(
                    content_type=content_type, name=tech, display_name=tech, is_active=True, field='technology'
                )

        except Exception as error:
            print(error)
