import csv
from dynamic_report.models import DBTable
from dynamic_report.models import Structure, Field
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "This command is for adding csv"
    def handle(self, *args, **options):
        try:
            filename = "recode.csv"
            index = 0
            with open(filename, mode ='r')as file:
                csvFile = csv.reader(file)
                for lines in csvFile:
                        if index >= 1:
                            breakpoint()
                            db = DBTable.objects.filter(name=lines[1]).first()
                            ty = Field.objects.filter(name=lines[2]).first()
                            stru = Structure.objects.filter(field_name=lines[0],db_table=db)
                            for sts in stru:
                                sts.field_type = ty
                                sts.save()
                                print("---->",ty.name)
                        else:
                            index += 1

        except Exception as error:
            print(error)
