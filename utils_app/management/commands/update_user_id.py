import csv
from employee.models import User, Team, Role
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "This command is for updating user"

    def handle(self, *args, **options):
        try:
            file = open(f"NameWise.csv", "r")
            csvFile = csv.reader(file) 
            file2 = open(f"NameWise1.csv", "w")
            csvwriter = csv.writer(file2)
            fields = ['Name', 'Team', 'Emplyee Id']
            csvwriter.writerow(fields)
            i = 0
            for lines in csvFile: 
                if i != 0 :
                    role = Role.objects.filter(name="engineer")
                    employee = User.objects.filter(role__in=role)
                    emp_id = None
                    for emp in employee:
                        if emp.employee_name.lower() == lines[0].lower():
                            emp_id = emp.employee_id
                            break
                    fields=[lines[0],lines[1],emp_id]
                    csvwriter.writerow(fields)
                i+=1
                
            file.close()
            file2.close()
        except Exception as error:
            print("---->\n",error)
