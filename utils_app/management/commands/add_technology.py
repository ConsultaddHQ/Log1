from django.core.management import BaseCommand

from project.models import ConsultantLeave
from utils_app.utils import create_cron_object
from utils_app.models import Choice, ContentType


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            consultant_qs = ConsultantLeave.objects.filter(year=2023, is_expired=True)
        except Exception as error:
            print(error)
