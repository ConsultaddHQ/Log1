import csv
from datetime import date, datetime, timedelta

from constance import config
from django.core.management import BaseCommand

from employee.models import User
from project.models import Project


class Command(BaseCommand):

    @staticmethod
    def get_total_hours(obj):
        try:
            start_dt = datetime.combine(obj.start_date, datetime.min.time())
            end_dt = datetime.combine(obj.end_date, datetime.min.time())

            diff = end_dt - start_dt
            months = int(diff.days) // 30
            weeks = round(int(diff.days - months * 30) // 7, 0)
            duration = months + weeks / 10
            return duration
        except Exception as e:
            print(str(e))

    @staticmethod
    def get_coders(obj):
        all_coders = {"name": [], "emp_id": []}
        queryset = obj.submission.screening.exclude(status='cancelled')
        for interview in queryset:
            coders = interview.guests.filter(type__in=['Coder', 'Coder & Assistant'])
            for item in coders:
                if item.user.employee_id not in all_coders.get("emp_id"):
                    all_coders["emp_id"].append(str(item.user.employee_id))
                    all_coders["name"].append(item.user.employee_name)
        return {
            "name": " \n ".join(all_coders["name"]),
            "emp_id": " \n ".join(all_coders["emp_id"])
        }

    @staticmethod
    def get_supervisor(obj):
        supervisors = {"name": [], "emp_id": []}
        queryset = obj.submission.screening.exclude(status='cancelled')
        for interview in queryset:
            if interview.supervisor.employee_id not in supervisors.get("emp_id"):
                supervisors["emp_id"].append(str(interview.supervisor.employee_id))
                supervisors["name"].append(interview.supervisor.employee_name)
        return {
            "name": " \n ".join(supervisors["name"]),
            "emp_id": " \n ".join(supervisors["emp_id"])
        }

    @staticmethod
    def get_support_person(obj):
        support_person = {"name": [], "emp_id": []}
        queryset = obj.support.filter(is_proxy_support=False)
        for item in queryset:
            if item.support.employee_id not in support_person.get("emp_id"):
                support_person["emp_id"].append(str(item.support.employee_id))
                support_person["name"].append(item.support.employee_name)
        return {
            "name": " \n ".join(support_person["name"]),
            "emp_id": " \n ".join(support_person["emp_id"])
        }

    @staticmethod
    def get_team_lead(obj):
        tl = User.objects.filter(team=obj.submission.marketing_team, role__name='admin').first()
        if tl:
            return {
                "name": tl.employee_name,
                "emp_id": tl.employee_id
            }
        else:
            return {}

    @staticmethod
    def get_recruiter(obj):
        if obj.consultant.recruiter:
            return {
                "name": obj.consultant.recruiter.employee_name, "emp_id": obj.consultant.recruiter.employee_id
            }
        return {}

    def handle(self, *args, **options):
        try:
            file = open("po_joined.csv", "w+")
            writer = csv.writer(file)
            writer.writerow([
                'Project ID', 'Consultant Name', 'Client', 'Vendor', 'Job Title', 'Project Type', 'Receive Date',
                'Start Date', 'End Date ', 'Duration', 'Is Remote', 'Current Status', 'Rate', 'Marketer',
                'Marketer EmpID', 'Recruiter', 'Recruiter EmpID', 'Supervisor', 'Supervisor EmpID', 'Coder',
                'Coder EmpID', 'Team Lead', 'Team Lead EmpID', 'VP', 'Support Persons', 'Support Persons EmpID',
                'PO Detail Page Link'
            ])

            project_qs = Project.objects.filter(
                statuses__status='received', statuses__created__gt='2024-11-30', statuses__created__lt='2025-01-01'
            )

            for obj in project_qs:
                received_date = obj.statuses.filter(status='received').first().created
                recruiter = self.get_recruiter(obj)
                total_hours = self.get_total_hours(obj)
                coders = self.get_coders(obj)
                supervisors = self.get_supervisor(obj)
                support_persons = self.get_support_person(obj)
                team_lead = self.get_team_lead(obj)
                vp = {
                    "name": "Arpit Mehta \n Aman Singh \n Vinal Khelani"
                }
                writer.writerow([
                    obj.id, obj.submission.consultant.name, obj.submission.client,
                    obj.submission.vendor.name, obj.submission.lead.job_title, obj.submission.get_work_type_display(),
                    received_date, obj.start_date, obj.end_date, total_hours, obj.is_remote, obj.status,
                    obj.submission.rate, obj.submission.created_by.employee_name, obj.submission.created_by.employee_id,
                    recruiter.get("name"), recruiter.get("emp_id"), supervisors.get("name", None),
                    supervisors.get("emp_id", None), coders.get("name", None), coders.get("emp_id", None), team_lead.get("name", None),
                    team_lead.get("emp_id", None), vp.get("name"), support_persons.get("name"), support_persons.get("emp_id"),
                    f"{config.APP_URL}#/details/{obj.submission.id}/project?id={obj.id}"
                ])
        except Exception as error:
            print(error)
