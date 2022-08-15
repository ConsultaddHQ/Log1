import csv
from employee.models import User, Team, Role
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "This command is for updating user"

    def handle(self, *args, **options):
        try:
            file = open(f"NameWise1.csv", "r")
            csvFile = csv.reader(file) 
            i = 0
            for lines in csvFile: 
                if i != 0 and len(lines[2]) > 0 :
                    employee = User.objects.filter(employee_id=lines[2]).first()
                    team = Team.objects.filter(name=lines[1]).first()
                    if employee is not None and team is not None:
                        employee.team = team
                        employee.save()
                i+=1
            file.close()

        except Exception as error:
            print("---->\n",error)
