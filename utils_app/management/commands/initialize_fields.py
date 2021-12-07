import json
from django.core.management import BaseCommand
from utils_app.models import ObjectGroup, Field


class Command(BaseCommand):
    help = "This command is for initialising Field and ObjectGroup model data"

    def handle(self, *args, **options):
        file = open("fields_fixture.json", "r")
        data = json.loads(file.read())
        file.close()

        for obj in data['fields']:
            Field.objects.get_or_create(
                name=obj['name'],
                model=obj['model'],
                app_label=obj['app_label'],
            )

        for obj in data['group']:
            obj_group, _ = ObjectGroup.objects.get_or_create(
                name=obj['name'],
                model=obj['model'],
                status=obj['status'],
            )
            for fie in obj['fields']:
                field = Field.objects.get(name=fie['name'], model=fie['model'], app_label=fie['app_label'])
                obj_group.fields.add(field)
