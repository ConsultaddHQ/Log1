from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            print("testing")
        except Exception as error:
            print(error)