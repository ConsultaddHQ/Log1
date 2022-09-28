from django.core.management import BaseCommand

from consultant.models import Consultant
from utils_app.utils import create_cron_error, create_cron_object, get_timezone
from utils_app.models import Choice, ContentType


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='add_technology')
        try:
            TECHNOLOGIES = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps',
                            'BA', 'DA', 'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce', 'Cyber Security']
            content_type = ContentType.objects.get(model='user')
            for technology in TECHNOLOGIES:
                chn = Choice.objects.create(name=technology, display_name=technology, content_type=content_type, field='technology')
        except Exception as error:
            print(error)
