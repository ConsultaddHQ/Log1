import xlrd
from django.core.management import BaseCommand

from employee.models import User, Role, Team
from utils_app.utils import create_cron_error


class Command(BaseCommand):
    help = "This command is to create user using spreadsheet."
    xlrd.xlsx.ensure_elementtree_imported(False, None)
    xlrd.xlsx.Element_has_iter = True

    def handle(self, *args, **options):

        try:
            loc = 'user_detail.xlsx'
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)
            for i in range(1, sheet.nrows):
                row = sheet.row_values(i)
                # [UserName, Employee_Name, Email, Phone, Gender, Team, Role]
                if User.objects.filter(email=row[2]).exists():
                    continue
                else:
                    try:
                        team = Team.objects.get(name=row[5])
                    except Team.DoesNotExist:
                        print(f'Email - {row[2]} - {row[5]} team does not exist in Log1')
                        continue
                    user = User.objects.create_user(
                        email=row[2],
                        team_id=team.id,
                        phone=int(row[3]),
                        gender=int(row[4]),
                        employee_id=int(row[1]),
                        name=row[0].capitalize(),
                        password='consultadd@123',
                    )
                    try:
                        role = Role.objects.get(name=row[6])
                        user.role.add(role)
                    except Role.DoesNotExist:
                        print(f"Email - {row[2]}, Role - {row[6]} does not exist. Please update role manually")
        except Exception as error:
            create_cron_error(error)
