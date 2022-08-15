import csv
from employee.models import User, Team, Role
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "This command is for creating team"

    def handle(self, *args, **options):
        try:
            file = open(f"TeamWise.csv", "r")
            csvFile = csv.reader(file) 
            i = 0
            for lines in csvFile: 
                if i != 0 and not Team.objects.filter(name=lines[0]):
                    Team.objects.create(name=lines[0],email=lines[1],dept=lines[2])
                    print("created",lines[0]) 
                i+=1
                
            file.close()
        except Exception as error:
            print("---->\n",error)
