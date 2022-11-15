import csv
from django.core.management import BaseCommand

from consultant.models import Consultant
from employee.models import Certificate
from utils_app.utils import create_cron_error, create_cron_object, get_timezone
from utils_app.models import Choice, ContentType


class Command(BaseCommand):
    def handle(self, *args, **options):
        job = create_cron_object(name='add_platform')
        try:
            content_type = ContentType.objects.get(model='test')
            platforms = ['CoderByte', 'Codility', 'Coderpad', 'CodeSignal', 'Amcat', 'Glider', 'FilteredAI', 'Kenexa',
                        'Hackerrank', 'Interviewmocha', 'Hirevue', 'Ikm', 'Mettl', 'PluralSight', 'LeetCode']
            for item in platforms:
                Choice.objects.create(name=item, display_name=item, content_type=content_type, field='platform')
        except Exception as error:
            print(error)
