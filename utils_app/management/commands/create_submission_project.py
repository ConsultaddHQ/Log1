from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.core.management import BaseCommand

from employee.models import User, Team
from marketing.models import Submission, Lead
from consultant.models import Consultant, ConsultantMarketing
from project.models import Project, ProjectStatus, TimeSheet

consultant_data = [
    {
        "name": "Sagar Sapkota",
        "email": "sagar.s@consultadd.com"
    },
    {
        "name": "Hardik Vagrecha",
        "email": "hardikvagrecha@gmail.com"
    },
    {
        "name": "Shaheryar Nadeem",
        "email": "shaheryar.n@consultadd.com"
    },
    {
        "name": "Sarah Karandy",
        "email": "sarah.k@consultadd.com"
    },
    {
        "name": "Rishika Gaur",
        "email": "gaur.rishika@gmail.com"
    },
    {
        "name": "Neha Kulkarni",
        "email": "neha161995@gmail.com"
    },
    {
        "name": "Prasad Dalal",
        "email": "prasad.d@consultadd.com"
    },
    {
        "name": "Gyanendra Singh Chandrawat",
        "email": "gyanendra.c@consultadd.com"
    },
    {
        "name": "Nisha Karki",
        "email": "nisha.k@consultadd.com"
    }
]


class Command(BaseCommand):

    @staticmethod
    def create_timesheet(obj, start_date=None, frequency=None, count=2):
        if not start_date:
            start_date = obj.start_date
        week_day = start_date.weekday()
        if week_day == 6:
            start_date = start_date + timedelta(days=1)
            week_day = start_date.weekday()
        if obj.submission.work_type == 'C2C':
            days = 6
        elif frequency == 'Biweekly':
            days = 13
        else:
            days = 6

        if frequency == 'Monthly':
            end_date = start_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        elif week_day == 0:
            end_date = start_date + timedelta(days=days)
        else:
            end_date = start_date + timedelta(days=days - week_day)

        for i in range(count):
            TimeSheet.objects.get_or_create(
                start=start_date, end=end_date,
                hours=0, status='draft', project=obj,
            )
            start_date = end_date + timedelta(days=1)
            end_date = end_date + timedelta(days=days + 1)

    def handle(self, *args, **options):
        try:
            CLIENT = "CAPS"
            date_ = datetime.strptime("2026-01-05", "%Y-%m-%d").date()
            marketer = User.objects.get(employee_id=3415)
            team = Team.objects.get(name="CAPS")
            lead = Lead.objects.get(id=119342)
            # for obj in consultant_data:
            # print(obj.get("email"))
            consultant = Consultant.objects.get(email="pruthvikpatel99@gmail.com")
            consultant_marketing_payload = {
                "consultant": consultant, "start": date_, "end": date_, "status": "close"
            }
            consultant_marketing_obj = ConsultantMarketing.objects.create(**consultant_marketing_payload)
            print(consultant_marketing_obj.id)
            payload = {
                "consultant_marketing": consultant_marketing_obj, "lead": lead,
                "created_by": marketer, "marketing_team": team, "status": "project",
                "employer": "Consultadd", "rate": 1, "client": CLIENT, "work_type": "c2c", "status": "archive"
            }
            sub = Submission.objects.create(**payload)
            lead.status = "sub"
            lead.save()

            project_payload = {
                "submission": sub, "consultant": consultant, "is_msg_sent": True, "rate": 0, "employer": "CloudTech",
                "support_required": False, "start_date": datetime.strptime("2026-01-05", "%Y-%m-%d")
            }
            po = Project.objects.create(**project_payload)
            ProjectStatus.objects.create(
                is_current=False, status="new", project=po
            )
            ProjectStatus.objects.create(
                is_current=False, status="received", project=po
            )
            ProjectStatus.objects.create(
                is_current=False, status="on_boarded", project=po
            )
            ProjectStatus.objects.create(status="joined", project=po)
            self.create_timesheet(po, start_date=date_)
            # print(f"PO Created for {obj.get('name')}")
        except Exception as error:
            print(f"error fetching {error}")
