import csv
from employee.models import User, Role
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "This command is for updating user"

    def handle(self, *args, **options):
        try:
            file = open(f"marketers.csv", "w")
            csvwriter = csv.writer(file)
            fields = ['Name', 'Emplyee Id', 'email']
            csvwriter.writerow(fields)

            role = Role.objects.filter(name="marketer")
            employee = User.objects.filter(role__in=role)

            for emp in employee:
                fields = []
                fields.append(emp.employee_name)
                fields.append(emp.employee_id)
                fields.append(emp.email)
                csvwriter.writerow(fields)
            file.close()
        except Exception as error:
            print("---->\n", error)