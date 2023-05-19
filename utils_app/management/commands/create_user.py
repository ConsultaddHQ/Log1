import csv
from django.core.management import BaseCommand

from employee.models import User, Role, Team


class Command(BaseCommand):
    help = "This command is to create user from CSV file."

    def handle(self, *args, **options):

        try:
            count = 0
            loc = 'data/users.csv'
            with open(loc, newline='') as csv_file:
                reader = csv.reader(csv_file, delimiter='\t', quotechar='|')
                next(reader)
                for row in reader:
                    if User.objects.filter(email=row[2]).exists():
                        continue
                    else:
                        try:
                            team = Team.objects.get(name__iexact=row[4])
                        except Team.DoesNotExist:
                            print(f'Email - {row[2]} - {row[4]} team does not exist in Log1')
                            continue
                        try:
                            user = User.objects.create_user(
                                team=team,
                                email=row[2],
                                gender='male',
                                phone=int(row[3]),
                                employee_id=int(row[1]),
                                name=row[0].capitalize(),
                                password='consultadd@123',
                            )
                            count += 1
                            try:
                                role = Role.objects.get(name__iexact=row[5])
                                user.role.add(role)
                            except Role.DoesNotExist:
                                print(f"Email - {row[2]}, Role - {row[5]} does not exist. Please update role manually")
                        except Exception as error:
                            print(error)
            print(count)
        except Exception as error:
            print(error)
