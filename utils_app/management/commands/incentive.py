import json
from datetime import datetime, date
from decimal import Decimal

import requests
from django.db.models import QuerySet
from django.core.management import BaseCommand
from django.shortcuts import get_object_or_404

from consultant.models import ConsultantPOC
from employee.models import User
from log1.utils import write_exception
from project.models import Project


MONTH_ID = "08"


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


def get_timestamp(date_time):
    if isinstance(date_time, str):
        date_time = datetime.strptime(date_time, "%Y-%m-%d")
    elif isinstance(date_time, date):
        date_time = datetime.combine(date_time, datetime.min.time())
    elif not date_time:
        return None
    return Decimal(date_time.timestamp())


def get_status(project):
    status_obj = project.statuses.filter(is_current=True).first()
    if not status_obj:
        return None
    status = status_obj.status
    if 'terminated' in status:
        return 'Terminated'
    elif 'cancelled' in status:
        return 'Cancelled'
    elif status in ['extended', 'joined']:
        return 'Joined'
    elif status in ['on_boarded', 'received']:
        return 'Received'
    else:
        return status_obj.get_status_display()


def get_datetime(date_time):
    if not date_time:
        return None
    elif isinstance(date_time, str):
        return date_time
    elif isinstance(date_time, date):
        return date_time.strftime("%Y-%m-%d")


def get_stakeholders_involved(project):
    marketing_team = project.submission.marketing_team.name
    if marketing_team != 'Consultadd Canada':
        vp = User.objects.filter(employee_id__in=[2572, 2491, 2667])
    else:
        vp = get_object_or_404(User, employee_id=2452)
    recruiter_poc = ConsultantPOC.objects.filter(
        consultant=project.submission.consultant, poc_type__iexact='Recruiter', end=None
    ).first()
    recruiter = recruiter_poc.poc if recruiter_poc else None
    support_persons = project.support.filter(is_proxy_support=False).values_list('support', flat=True)
    team_lead = User.objects.filter(
        role__name='admin', team=project.submission.marketing_team, is_active=True, account_login=True
    ).first()
    supervisors = project.submission.screening.exclude(status='cancelled')
    coders = project.submission.screening.exclude(status='cancelled').filter(
        guests__type__in=['Coder', 'Coder & Assistant']
    ).values_list('guests__user__employee_id', flat=True)
    stakeholders = {
        "VP": get_employee_info(vp),
        "Coder": get_employee_info(coders),
        "TeamLead": get_employee_info(team_lead),
        "Recruiter": get_employee_info(recruiter),
        "Supervisor": get_employee_info(supervisors, "supervisor"),
        "SupportPerson": get_employee_info(support_persons),
        "Marketer": get_employee_info(project.submission.created_by)
    }
    return stakeholders


def share_po_stakeholder_info(project, request=None):
    try:
        start_date_timestamp, start_date_datetime = get_timestamp(project.start_date), get_datetime(project.start_date)
        received_at = project.statuses.filter(status='received').first()
        received_at_timestamp, received_at_datetime = \
            (get_timestamp(received_at.created), get_datetime(received_at.created)) \
                if received_at else (get_timestamp(datetime.now()), get_datetime(datetime.now()))
        joined_at = project.statuses.filter(status='joined').first()
        joined_at_timestamp, joined_at_datetime = (get_timestamp(joined_at.created), get_datetime(joined_at.created)) \
            if joined_at else (None, None)

        stakeholder_data = {
            "month_id": int(f"2024{MONTH_ID}"),
            "ProjectID": project.id,
            "JoinedDate": joined_at_timestamp,
            "JoinedDateStr": joined_at_datetime,
            "Client": project.submission.client,
            "POStartDate": start_date_timestamp,
            "POStartDateStr": start_date_datetime,
            "SubmissionID": project.submission.id,
            "OfferReceivedDate": received_at_timestamp,
            "ProjectCurrentStatus": get_status(project),
            "OfferReceivedDateStr": received_at_datetime,
            "ConsultantName": project.submission.consultant.name,
            "MarketingTeam": project.submission.marketing_team.name,
            "StakeHolderInvolved": get_stakeholders_involved(project),
            "MarketerEmpID": project.submission.created_by.employee_id,
            "MarketerName": project.submission.created_by.employee_name,
            "MarketerTeamName": project.submission.created_by.team.name,
            "ConsultantQueryName": get_query_name(project.submission.consultant.name),
            "MarketerQueryName": get_query_name(project.submission.created_by.employee_name),
            "MarketingTeamQueryName": get_query_name(project.submission.created_by.team.name),
            "WorkType": "W2" if project.submission.get_work_type_display() != "C2C" else "C2C"
        }
        return stakeholder_data
    except Exception as error:
        write_exception(error, request)


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            count = "05"

            url = "https://81dwg4mwy6.execute-api.ap-south-1.amazonaws.com"
            # url = "http://localhost:3000/incentive/trigger/project"
            project_qs = Project.objects.filter(
                statuses__status='received', statuses__created__gte=f"2024-{MONTH_ID}-01", statuses__created__lt=f"2024-{int(MONTH_ID)+1}-01"
            )
            # project_qs = Project.objects.filter(id=1527)

            print(len(project_qs))
            trigger_url = f"{url}/incentive/trigger/project"
            breakpoint()
            for project in project_qs:
                incentive_json = share_po_stakeholder_info(project)

                # dump_data = json.dumps(incentive_json)

                resp = requests.post(trigger_url, json=incentive_json)
                # resp = requests.post(url, data=dump_data)

                if resp.status_code == 200:
                    count += 1
                    print(f"{count}")
                    print("Data Added Successfully")
                else:
                    print("Not Done")

            pay_loss_resp = requests.get(f"{url}/incentive/mark_pay_loss?month_id=2024{MONTH_ID}")
            if pay_loss_resp.status_code == 200:
                print("PayLoss Marked")

            pay_release_resp = requests.get(f"{url}/incentive/release?month_id=2024{MONTH_ID}")
            if pay_release_resp.status_code == 200:
                print("Pay Release Marked")

            el_resp = requests.get(f"{url}/incentive/trigger/eligibility?month_id=2024{int(MONTH_ID)+1}")
            if el_resp.status_code == 200:
                print("Eligibility Marked")

            # incentive_json = share_po_stakeholder_info(project_qs[4])
            # dump_data = json.dumps(incentive_json)
            # resp = requests.post("http://localhost:3000/incentive/trigger/project", data=dump_data)

        except Exception as error:
            print(error)
