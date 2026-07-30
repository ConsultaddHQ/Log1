import json
from datetime import datetime, date
from django.db.models import QuerySet
from django.core.management import BaseCommand

from employee.models import User
from project.models import Project

stakeholder_json = {
    "Marketer": 0, "Recruiter": 0, "Supervisor": 0, "Coder": 0,
    "Team Lead": 0, "LeadSM": 0, "VP": 0, "SupportPersons": 0
}


def get_name_id_dict(emp_qs):
    if (type(emp_qs) is list) or (isinstance(emp_qs, QuerySet)):
        name_id_list = []
        for emp_obj in emp_qs:
            name_id_list.append(
                {"empID": str(emp_obj.employee_id), "empName": emp_obj.employee_name, "empTeam": emp_obj.team.name}
            )
        return name_id_list
    else:
        return {"empID": str(emp_qs.employee_id), "empName": emp_qs.employee_name, "empTeam": emp_qs.team.name}


class Command(BaseCommand):

    @staticmethod
    def get_current_status(obj, duration):
        status = obj.statuses.filter(is_current=True).first().status
        if status == 'joined':
            if duration >= 1000:
                return "Completed"
            else:
                return "InProgress"
        else:
            if duration >= 1000:
                return "Completed"
            else:
                return "InProgress"

    @staticmethod
    def get_duration(obj):
        status = obj.statuses.filter(is_current=True).first().status
        if status == 'joined':
            duration = (date.today() - obj.start_date).days * 8
        else:
            duration = (date.today() - obj.statuses.filter().order_by('-id').first().created.date()).days * 8
        return duration

    @staticmethod
    def fetch_stakeholders(obj):
        coders = []
        screening_qs = obj.submission.screening.all()
        tl = User.objects.filter(
            role__name='admin', team=obj.submission.marketing_team, is_active=True, account_login=True
        ).first()
        for screening_obj in screening_qs:
            coders_qs = screening_obj.guests.filter(type__in=['Coder', 'Coder & Assistant'])
            if coders_qs:
                coders.extend([item.user for item in coders_qs])

        recruiter = None
        coders = list(set(coders))
        coder = get_name_id_dict(coders)
        marketer = get_name_id_dict(obj.created_by)
        team_lead = get_name_id_dict(tl) if tl else None
        supervisor = get_name_id_dict([item.supervisor for item in screening_qs])
        support_persons = get_name_id_dict([item.support for item in obj.support.filter(is_proxy_support=False)])
        vp = get_name_id_dict(User.objects.get(
            employee_id=2572 if obj.submission.marketing_team.name != "Consultadd Canada" else 2452)
        )
        lead_sm = get_name_id_dict(
            User.objects.get(employee_id=2491)
        ) if obj.submission.marketing_team.name != "Consultadd Canada" else {}
        stakeholders = {
            "Marketer": marketer, "Recruiter": recruiter, "Team Lead": team_lead,
            "VP": vp, "LeadSM": lead_sm, "Coder": coder, "Supervisor": supervisor, "SupportPersons": support_persons
        }
        return stakeholders

    @staticmethod
    def add_stakeholder(emp_id, key):
        return {
            "EmpName": User.objects.get(employee_id=emp_id).employee_name,
            "EmpTeam": User.objects.get(employee_id=emp_id).team.name,
            "Stakeholder Type": key
        }

    @staticmethod
    def update_json(emp_id, key):
        return {
            "EmpName": User.objects.get(employee_id=emp_id).employee_name,
            "EmpTeam": User.objects.get(employee_id=emp_id).team.name,
            "Stakeholder Type": key
        }

    def handle(self, *args, **options):
        project_data_json = {}
        project_qs = Project.objects.filter(created__gte='2023-11-01', statuses__status='received')
        for obj in project_qs:
            joined = obj.statuses.filter(status='joined').first()
            duration = self.get_duration(obj) if joined else 0
            project_data_json[obj.id] = {
                "Hours": duration,
                "Client": obj.submission.client,
                "TotalPayout": stakeholder_json,
                "SubmissionID": str(obj.submission.id),
                "Marketer": obj.created_by.employee_name,
                "Consultant": obj.submission.consultant.name,
                "MarketingTeam": obj.submission.marketing_team.name,
                "StakeholdersInvolved": self.fetch_stakeholders(obj),
                "JoinedAt": datetime.strftime(joined.created, "%Y-%m-%d") if joined else None,
                "CurrentStatus": self.get_current_status(obj, duration) if joined else "NotJoined",
                "LastUpdatedAt": None, "Modified": None, "Created": datetime.strftime(datetime.now(), "%Y-%m-%d"),
                "ReceivedAt": datetime.strftime(obj.statuses.filter(status='received').first().created, "%Y-%m-%d"),
                "pay_calculated": {
                    "160 Hours": False, "320 Hours": False, "480 Hours": False,
                    "640 Hours": False, "800 Hours": False, "1000 Hours": False
                }
            }

        project_write_json = json.dumps(project_data_json, indent=4)
        with open("project_data.json", "w") as outfile:
            outfile.write(project_write_json)
