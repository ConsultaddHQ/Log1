import json
import logging
import requests
from datetime import datetime, date, timedelta

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City
from employee.models import User, Team
from consultant.models import Consultant
from employee.serializers import UserSerializer
from marketing.models import Submission, Interview
from project.models import Project, PROJECT_STATUS_CHOICES

logger = logging.getLogger(__name__)


def mattermost_webhook(url, data):
    headers = {'Content-Type': 'application/json'}
    requests.post(url, headers=headers, data=json.dumps(data))


class CityViewSets(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query')
        city = City.objects.filter(name__istartswith=query)
        data = city[:40].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)


class SlashCommandViewSets(GenericViewSet):
    authentication_classes = ()
    queryset = User.objects.all()
    permission_classes = ()
    serializer_class = UserSerializer
    months = ["Unknown", "January", "February", "March", "April", "May", "June", "July", "August", "September",
              "October", "November", "December"]

    def team_data_by_day(self, day, month, year, command):
        text = f"""#### Team Status :memo: \n
Date - {self.months[month]} {day}, {year}
command - {command}\n
| Team Name | Scrum Master | Current Bench | Submission | Interview | Offer | Joined |
|:----------|:-------------|:--------------|:-----------|:----------|:------|:-------|
"""

        teams = Team.objects.filter(dept='Marketing')
        for team in teams:
            bench_consultant = Consultant.objects.filter(
                marketing__teams__name__iexact=team.name,
                marketing__status='open'
            ).count()
            submission_count = Submission.objects.filter(
                created__day=day,
                created__year=year,
                created__month=month,
                created_by__team__name__iexact=team.name
            ).exclude(status='draft').count()
            interview_count = Interview.objects.filter(
                created__day=day,
                created__year=year,
                created__month=month,
                submission__created_by__team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            offer_count = Project.objects.filter(
                statuses__created__day=day,
                statuses__created__year=year,
                statuses__created__month=month,
                statuses__status__in=['received', 'on_boarded'],
                submission__created_by__team__name__iexact=team.name,
            ).count()
            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__day=day,
                statuses__created__year=year,
                statuses__created__month=month,
                submission__created_by__team__name__iexact=team.name,
            ).count()
            scrum_masters = User.objects.filter(team__name__iexact=team.name, role__name='admin', is_active=True)
            scrum_master = None
            if scrum_masters:
                scrum_master = ", ".join(list(scrum_masters.values_list('employee_name', flat=True)))

            text += f"| {team.name.title()} | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count}  |\n"

        scrum_master = "Sudeep B."
        bench_consultant = Consultant.objects.filter(marketing__status='open').count()
        submission_count = Submission.objects.filter(
            created__day=day,
            created__year=year,
            created__month=month
        ).exclude(status='draft').count()

        interview_count = Interview.objects.filter(
            created__day=day,
            created__year=year,
            created__month=month,
        ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()

        offer_count = Project.objects.filter(
            statuses__created__day=day,
            statuses__created__year=year,
            statuses__created__month=month,
            statuses__status__in=['received', 'on_boarded'],
        ).count()

        joined_count = Project.objects.filter(
            statuses__status='joined',
            statuses__created__day=day,
            statuses__created__year=year,
            statuses__created__month=month,
        ).count()

        text += f"| Total | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count} |\n"

        return text

    def team_data_by_start(self, start, command):
        text = f"""#### Team Status :memo: \n
From Date - {start} to {str(date.today())}
command - {command}\n
| Team Name | Scrum Master | Current Bench | Submission | Interview | Offer | Joined |
|:----------|:-------------|:--------------|:-----------|:----------|:------|:-------|
"""

        teams = Team.objects.filter(dept='Marketing')
        for team in teams:
            bench_consultant = Consultant.objects.filter(
                marketing__teams__name__iexact=team.name,
                marketing__status='open'
            ).count()
            submission_count = Submission.objects.filter(
                created__gte=start,
                created_by__team__name__iexact=team.name
            ).exclude(status='draft').count()
            interview_count = Interview.objects.filter(
                created__gte=start,
                submission__created_by__team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            offer_count = Project.objects.filter(
                statuses__created__gte=start,
                statuses__status__in=['received', 'on_boarded'],
                submission__created_by__team__name__iexact=team.name,

            ).count()
            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__gte=start,
                submission__created_by__team__name__iexact=team.name,
            ).count()
            scrum_masters = User.objects.filter(team__name__iexact=team.name, role__name='admin', is_active=True)
            scrum_master = None
            if scrum_masters:
                scrum_master = ", ".join(list(scrum_masters.values_list('employee_name', flat=True)))

            text += f"| {team.name.title()} | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count}  |\n"

        scrum_master = "Sudeep B."
        bench_consultant = Consultant.objects.filter(marketing__status='open').count()
        submission_count = Submission.objects.filter(created__gte=start).exclude(status='draft').count()
        interview_count = Interview.objects.filter(
            created__gte=start).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
        offer_count = Project.objects.filter(
            statuses__status__in=['received', 'on_boarded'], statuses__created__gte=start
        ).count()
        joined_count = Project.objects.filter(
            statuses__status='joined',
            statuses__created__gte=start,
        ).count()

        text += f"| Total | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count} |\n"

        return text

    def team_data_by_month(self, month, year, command):
        text = f"""#### Team Status :memo: \n
Date - {self.months[month]}/{year}
command - {command}\n\n
| Team Name | Scrum Master | Current Bench | Submission | Interview | Offer | Joined |
|:----------|:-------------|:--------------|:-----------|:----------|:------|:-------|
"""

        teams = Team.objects.filter(dept='Marketing')
        for team in teams:
            bench_consultant = Consultant.objects.filter(
                marketing__status='open',
                marketing__teams__name__iexact=team.name,
            ).count()

            submission_count = Submission.objects.filter(
                created__year=year,
                created__month=month,
                created_by__team__name__iexact=team.name
            ).exclude(status='draft').count()

            interview_count = Interview.objects.filter(
                created__month=month, created__year=year,
                submission__created_by__team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()

            offer_count = Project.objects.filter(
                statuses__created__year=year,
                statuses__created__month=month,
                statuses__status__in=['received', 'on_boarded'],
                submission__created_by__team__name__iexact=team.name,
            ).count()

            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__year=year,
                statuses__created__month=month,
                submission__created_by__team__name__iexact=team.name,
            ).count()

            scrum_masters = User.objects.filter(team__name=team.name, role__name='admin', is_active=True)
            scrum_master = None
            if scrum_masters:
                scrum_master = ", ".join(list(scrum_masters.values_list('employee_name', flat=True)))

            text += f"| {team.name.title()} | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count} |\n"

        scrum_master = "Sudeep B."
        bench_consultant = Consultant.objects.filter(marketing__status='open').count()

        submission_count = Submission.objects.filter(
            created__year=year,
            created__month=month,
        ).exclude(status='draft').count()

        interview_count = Interview.objects.filter(
            created__year=year,
            created__month=month,
        ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()

        offer_count = Project.objects.filter(
            statuses__created__year=year,
            statuses__created__month=month,
            statuses__status__in=['received', 'on_boarded'],
        ).count()

        joined_count = Project.objects.filter(
            statuses__status='joined',
            statuses__created__year=year,
            statuses__created__month=month,
        ).count()

        text += f"| Total | {scrum_master} | {bench_consultant} | {submission_count} | {interview_count} | {offer_count} | {joined_count} |\n"

        return text

    @action(methods=['get'], detail=False, url_path='consultant')
    def consultant(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('text', None)
            command = request.query_params.get('command', None)

            if not query and len(query) > 3:
                return Response({"text": f"{command} {query} \n Bad Input"}, status=status.HTTP_200_OK)

            data_type = query.split(" ")[0]
            name = query.split(" ")[1]

            consultants = Consultant.objects.filter(name__istartswith=name).exclude(status='archived')
            text = "Bad Input"

            if data_type == 'poc':
                text = f"""#### Consultant POC :memo: \n
command - {command} {query}\n
| Name | Email | Status | Team | Marketer | Recruiter | Retention |
|:-----|:------|:-------|:-----|:---------|:----------|:----------|
"""
                for consultant in consultants:
                    retention = consultant.relation.employee_name if consultant.relation else None
                    recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                    marketing = consultant.marketing.filter(status='open')
                    primary_marketer_name = marketing.first().primary_marketer.employee_name if marketing else None
                    primary_marketer_team = marketing.first().primary_marketer.team.name if marketing else None
                    text += f"| {consultant.name} | {consultant.email} |  {consultant.status} | {primary_marketer_team} | {primary_marketer_name} |  {recruiter} |  {retention} |\n"

            elif data_type == 'info':
                text = f"""#### Consultant INFO :memo: \n
command - {command} {query}\n
| Name | Email | DOB | Status | Visa | Phone No | Skill | Preferred Location |
|:-----|:------|:----|:-------|:-----|:---------|:------|:-------------------|
"""
                for consultant in consultants:
                    visa_type = consultant.work_auth.filter(is_current=True).first().visa_type
                    marketing = consultant.marketing.filter(status='open')
                    pref_location = marketing.first().preferred_location.replace('\r\n', ', ') if marketing else None
                    text += f"""| {consultant.name} | {consultant.email} | {consultant.date_of_birth} | {consultant.status} | {visa_type} | {consultant.phone_no} | {consultant.skills} | {pref_location} |\n"""

            elif data_type == 'status':
                text = f"""#### Consultant STATUS :memo: \n
command - {command} {query}\n
| Name | Days On Bench | Status | Submission | Interview | Project |
|:-----|:--------------|:-------|:-----------|:----------|:--------|
"""
                for consultant in consultants:
                    marketing = consultant.marketing.filter(status='open')
                    if marketing:
                        days_on_bench = (date.today() - marketing.first().start).days
                    else:
                        days_on_bench = None
                    submission_count = Submission.objects.filter(consultant_marketing__consultant=consultant).exclude(
                        status='cancelled').count()
                    interview_count = Interview.objects.filter(
                        submission__consultant_marketing__consultant=consultant
                    ).exclude(status='cancelled').distinct('submission').order_by().count()
                    project_count = Project.objects.filter(consultant=consultant).count()

                    text += f"| {consultant.name} | {days_on_bench} | {consultant.status} | {submission_count} | {interview_count} | {project_count} |\n"

            return Response({"text": text}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"text": f"Bad Request"}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='marketer')
    def marketer(self, request):
        try:
            query = request.query_params.get('text', None)
            command = request.query_params.get('command', None)
            if not query and len(query) < 3:
                return Response({"text": f"{command} {query} \n Bad Input"}, status=status.HTTP_200_OK)

            date_filter = query.split(" ")[0]
            name = query.split(" ")[1]
            employees = User.objects.filter(employee_name__istartswith=name, team__dept='Marketing', is_active=True)

            if date_filter == 'week':
                start = datetime.today() - timedelta(days=7)
            else:
                start = datetime.today() - timedelta(days=30)
            text = f"""#### Marketer Status :memo: \n
Date Range - {str(start.date())} - {str(date.today())}\n
command - {command} {query}\n
| Name | Team | Submission | Interview | Offer | Consultant Assigned |
|:-----|:-----|:-----------|:----------|:------|:--------------------|
"""
            for user in employees:
                con_assigned = ", ".join(
                    list(user.marketed.filter(status='open').values_list('consultant__name', flat=True)))
                submission_count = Submission.objects.filter(
                    created_by=user, created__gte=start
                ).exclude(status='cancelled').count()
                interview_count = Interview.objects.filter(
                    submission__created_by=user, created__gte=start
                ).exclude(status='cancelled').count()
                offer_count = Project.objects.filter(
                    statuses__status='received',
                    submission__created_by=user,
                    statuses__created__gte=start,
                ).count()
                consultant_assigned = con_assigned if len(con_assigned) > 0 else None

                text += f"""| {user.employee_name} | {user.team.name} |  {submission_count} | {interview_count} | {offer_count} |  {consultant_assigned} |\n"""
            return Response({"text": text}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"text": f"Bad Request"}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            query = request.query_params.get('text', None)
            command = request.query_params.get('command', None)
            arguments = query.split()
            slash_command = f"{command} {query}"
            if not query and len(arguments) > 0:
                return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)
            text = slash_command
            arg1 = arguments[0]

            if arg1 == 'month':
                if len(arguments) == 1:
                    start = date.today() - timedelta(days=30)
                    text = self.team_data_by_start(start, slash_command)

                elif len(arguments) == 2:
                    arg2 = arguments[1]
                    this_month = datetime.today().month
                    year = datetime.today().year
                    month = int(arg2) if arg2.isdigit() else None
                    if not month:
                        return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)
                    if month > this_month:
                        year = datetime.today().year - 1
                    text = self.team_data_by_month(month, year, slash_command)

            elif arg1 == 'day':
                this_month = datetime.today().month
                year = datetime.today().year
                if len(arguments) == 1:
                    day = date.today().day
                    text = self.team_data_by_day(day, this_month, year, slash_command)

                elif len(arguments) == 2:
                    arg2 = arguments[1]
                    day = int(arg2) if arg2.isdigit() else None
                    if not day:
                        return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)
                    text = self.team_data_by_day(day, this_month, year, slash_command)

                elif len(arguments) == 3:
                    arg1 = arguments[1]
                    arg2 = arguments[2]
                    day = int(arg1) if arg1.isdigit() else None
                    month = int(arg2) if arg2.isdigit() else None
                    if not day:
                        return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)
                    if not month:
                        return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)
                    if month > this_month:
                        year = datetime.today().year - 1
                    text = self.team_data_by_day(day, month, year, slash_command)

            elif arg1 == 'week':
                start = date.today() - timedelta(days=7)
                text = self.team_data_by_start(start, slash_command)

            elif arg1 == 'bench' and len(arguments) > 1:
                arg2 = arguments[1]
                if arg2.lower() == 'consultadd':
                    text = f"""#### Team Status :memo: \n
Team - {arg2.title()}
command - {slash_command}\n
| Name | Email | Phone No | Teams | Status | In Pool | RTG | Marketing Start | Recruiter | Preferred Location |
|:-----|:------|:---------|:------|:-------|:--------|:----|:----------------|:----------|:-------------------|
"""
                    bench_consultant = Consultant.objects.filter(marketing__status='open')
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        teams = ", ".join(list(marketing.teams.all().values_list('name', flat=True)))
                        text += f"| {consultant.name} | {consultant.email} | {consultant.phone_no} | {teams} | {consultant.status} | {marketing.in_pool} | {marketing.rtg} | {str(marketing.start)} | {recruiter} | {preferred_location} |\n"

                else:
                    text = f"""#### Team Status :memo: \n
Team - {arg2.title()}
command - {slash_command}\n
| Name | Email | Phone No | Status | In Pool | RTG | Marketing Start | Recruiter | Preferred Location |
|:-----|:------|:---------|:-------|:--------|:----|:----------------|:----------|:-------------------|
"""
                    bench_consultant = Consultant.objects.filter(
                        marketing__status='open',
                        marketing__teams__name__iexact=arg2,
                    )
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        text += f"| {consultant.name} | {consultant.email} | {consultant.phone_no} | {consultant.status} | {marketing.in_pool} | {marketing.rtg} | {str(marketing.start)} |  {recruiter} | {preferred_location} |\n"

            else:
                return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)

            return Response({"text": text}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"text": str(error)}, status=status.HTTP_200_OK)
