import csv
from django.core.management import BaseCommand

from employee.models import User, Team, Role


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            team = Team.objects.get(name='Consultadd')

            legal = Role.objects.get(name='legal')
            trainer = Role.objects.get(name='trainer')
            engineer = Role.objects.get(name='engineer')
            marketer = Role.objects.get(name='marketer')
            recruiter = Role.objects.get(name='recruiter')
            business = Role.objects.get(name='business')

            with open('candidates.csv', newline='') as csv_file:
                reader = csv.reader(csv_file, delimiter=',', quotechar='|')
                next(reader)
                for row in reader:
                    try:
                        qs = User.objects.filter(email=row[2].strip().lower())
                        if qs:
                            continue
                        qs = User.objects.filter(employee_name__iexact=row[1].strip().lower())
                        if qs:
                            continue

                        role_name = row[3].strip().lower()
                        if role_name == 'marketing':
                            role = marketer
                        elif role_name == 'engineering':
                            role = engineer
                        elif role_name == 'training':
                            role = trainer
                        elif role_name == 'recruitment':
                            role = recruiter
                        elif role_name == 'business':
                            role = business
                        elif role_name == 'legal':
                            role = legal
                        else:
                            print("Role not found")
                            print(row)
                            continue

                        user = User.objects.create(
                            role=role,
                            team=team,
                            gender='male',
                            phone='1234567890',
                            username=row[0].strip(),
                            employee_id=row[0].strip(),
                            email=row[2].strip().lower(),
                            employee_name=row[1].strip().title(),
                        )
                    except Exception as error:
                        print(row)
                        print(error)

        except Exception as error:
            print(str(error))
