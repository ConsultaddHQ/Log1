from django.core.management import BaseCommand
from django.conf import settings
from django.apps import apps

from dynamic_report.models import DBTable
# from dynamic_reports.models import DBModel


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            all_apps = settings.PROJECT_APPS
            for app in all_apps:
                ap = app.split(".")[0]
                modules = list(apps.get_app_config(ap).models.values())
                for mod in modules:
                    single_mod = str(mod).split(".")
                    modul = single_mod[len(single_mod)-1].replace(".","").replace(">","").replace("'","")
                    model_name = apps.get_model(ap, modul)
                    count = 0
                    for f in model_name._meta.fields:
                        count+=f.__dict__['is_relation'] == False
                    DBTable.objects.create(name=modul, app_name=ap, own_property_count=count)
        except Exception as error:
            print(error)