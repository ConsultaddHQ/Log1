import csv

from django.core.management import BaseCommand
from django.db.models import QuerySet

from consultant.models import ConsultantPOC
from employee.models import User
from project.models import Project


def get_user_info(user_obj):
    if not user_obj:
        return dict()
    return {
        "EmpTeam": user_obj.team.name,
        "EmpName": user_obj.employee_name,
        "EmpID": int(user_obj.employee_id)
    }


def get_query_name(keyword):
    if keyword:
        return " ".join(keyword.lower().split(" "))
    return keyword


def get_employee_info(queryset, user_type=None):
    if user_type == "supervisor":
        supervisor_data = []
        for interview in queryset:
            supervisor_info = get_user_info(interview.supervisor)
            supervisor_info.update({"Round": f"Round-{interview.round}"})
            supervisor_data.append(supervisor_info)
        return supervisor_data
    if isinstance(queryset, (list, QuerySet)):
        queryset = [v for v in queryset if v is not None]
        if all(isinstance(obj, int) for obj in queryset):
            user_objs = User.objects.filter(employee_id__in=queryset)
            emp_info = [get_user_info(user_obj) for user_obj in user_objs]
        else:
            emp_info = [get_user_info(obj) for obj in queryset]
        return emp_info

    if isinstance(queryset, int):
        queryset = User.objects.filter(employee_id=queryset).first()
        if not queryset:
            return None

    return get_user_info(queryset)



class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            col_name = [
                "Project ID", "Marketer Name", "Client Name", "Employer Name", "Company Name", "Start Date", "End Date",
                "Duration",	"Remote", "Project Type", "Status",	"Rate",	"Consultant",	"Supervisor", 	"Coder", 	"Recruiter"
            ]
            file = open("data_report.csv", "w+")
            writer = csv.writer(file)
            writer.writerow(col_name)
            project_qs = Project.objects.filter(
                statuses__status='received', statuses__created__gte="2024-11-01", statuses__created__lt="2024-12-01"
            )
            for project in project_qs:
                supervisors = get_employee_info(project.submission.screening.exclude(status='cancelled'), "supervisor")
                coders = get_employee_info(project.submission.screening.exclude(status='cancelled').filter(
                    guests__type__in=['Coder', 'Coder & Assistant']
                ).values_list('guests__user__employee_id', flat=True))
                recruiter_poc = ConsultantPOC.objects.filter(
                    consultant=project.submission.consultant, poc_type__iexact='Recruiter', end=None
                ).first()
                recruiter = get_employee_info(recruiter_poc.poc) if recruiter_poc else None

                writer.writerow([
                    project.id, project.submission.created_by.employee_name, project.submission.client, project.employer,
                    project.submission.vendor.name, project.start_date, project.end_date, project.duration, project.is_remote, project.submission.get_work_type_display(),
                    project.status, project.rate, project.submission.consultant.name, supervisors, coders, recruiter
                ])
        except Exception as e:
            print(str(e))