import csv

from django.core.management import BaseCommand
from django.contrib.auth.models import ContentType

from utils_app.models import City, Choice
from consultant.models import Consultant


class Command(BaseCommand):
    help = "This is one time command to move user avatar to AWS-S3 bucket"

    def handle(self, *args, **options):
        try:
            content = ContentType.objects.get(model='workauth')
            choices = Choice.objects.filter(field='visa')
            for choice in choices:
                choice.field = "visa_usa"
                choice.save()
            visa = [
                {
                    "display_name": "Open Work Permit", "name": "OWP", "field": "visa_ca"
                },
                {
                    "display_name": "TN Visa", "name": "TN permit", "field": "visa_ca"
                },
                {
                    "display_name": "Canadian PR", "name": "PR", "field": "visa_ca"
                }
            ]
            for v in visa:
                Choice.objects.create(
                    name=v['name'], display_name=v['display_name'], field=v['field'], content_type=content
                )
        except Exception as error:
            print(error)
