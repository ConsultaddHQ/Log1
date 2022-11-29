from django.core.management import BaseCommand
from django.conf import settings
from django.apps import apps

from dynamic_report.models import DBTable, Field, Structure
# from dynamic_reports.models import DBModel


def get_display_name(name):
    display_name = ""
    name_array = name.split("_")
    for ele in name_array:
        display_name += ele[0].upper()+ele[1:]+" "
    return display_name[:len(display_name)-1]
        

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            allTable = DBTable.objects.all()
            for table in allTable:
                model = apps.get_model(table.app_name, table.name)
                if model:
                    for fild in model._meta.fields:
                        # need to check if there any field exist or not
                        name = fild.name
                        front_ref = None
                        back_ref = None
                        if fild.__dict__['is_relation']:
                            front_ref = name
                        field_name = str(type(fild)).split('.')[-1].split("'")[0]
                        exist_field = Field.objects.filter(name=field_name).first()
                        db_table = DBTable.objects.filter(name=str(model).split('.')[-1].split("'")[0]).first()
                        if not exist_field:
                            exist_field = Field.objects.create(name=field_name)
                            
                        Structure.objects.create(field_name=name, display_name=get_display_name(name), front_ref=front_ref, back_ref=back_ref,field_type=exist_field, db_table=db_table)
            
        except Exception as error:
            print(error)