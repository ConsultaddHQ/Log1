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
            loc = 'data/new_joining.xlsx'
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)
            for i in range(1, sheet.nrows):
                row = sheet.row_values(i)
                # [UserName, Employee_Name, Email, Phone, Team, Role]
                if User.objects.filter(email=row[2]):
                    continue
                else:
                    team = Team.objects.get(name=row[4])
                    user = User.objects.create_user(
                        int(row[1]), row[2], row[0].capitalize(), team, int(row[3]), 'consultadd'
                    )
                    role = Role.objects.get(name=row[5])
                    user.role.add(role)
        except Exception as error:
            create_cron_error(error)
