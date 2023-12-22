import csv
import json
import copy
from datetime import datetime, date, timedelta

from django.db import transaction
from rest_framework import status
from django.db.models import Q, Max
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config

from api_key.models import APIKey
from employee.models import Team, User
from utils_app.models import ScrumMeeting
from utils_app.utils import export_to_csv
from activity.views import create_activity
from utils_app.thred_mail import send_email
from engineering.models import ProjectUpdate
from engineering.utils import tag_and_notify
from employee.serializers import UserSerializer
from attachment.models import create_attachment
from engineering.serializers import ProjectUpdateSerializer
from report.serializers import ReportSerializer, ConsultantInfoSerializer, SubmissionInfoSerializer, \
    InterviewInfoSerializer, ProjectInfoSerializer, TimesheetProjectSerializer, TimesheetTestSerializer, \
    TimesheetUserSerializer
from log1.utils import write_exception, ERROR_MSG
from project.models import Project, ProjectSupport
from marketing.models import Submission, Interview, Test
from consultant.models import ConsultantMarketing, Consultant
from project.serializers import ProjectSupportDetailSerializer
from log1.utils import post_msg_using_webhook, get_page_limits


ERR_DURATION = "Please duration for the report"


# Route - /report/
class ScrumMeetingReport(GenericViewSet):
    queryset = ScrumMeeting.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='scrum_meeting')
    def scrum_meeting(self, request):
        scrum_meeting = ScrumMeeting.objects.filter(previous=True)
        if scrum_meeting:
            previous_meeting_date = scrum_meeting.first().held_on
            teams = Team.objects.filter(dept="Marketing")
            text = f"""
#### Scrum Report ({str(previous_meeting_date)} - {str(date.today())}) :chart_with_upwards_trend:\n
| Team | Interviews | Offers | Bench | Pool |
|:-----|:-----------|:-------|:------|:-----|
"""
            for team in teams:
                team_name = team.name
                pool = ConsultantMarketing.objects.filter(
                    teams__name=team_name, in_pool=True,
                    status='open'
                ).distinct('consultant').order_by().count()
                bench = ConsultantMarketing.objects.filter(
                    teams__name=team_name, in_pool=False,
                    status='open'
                ).distinct('consultant').order_by().count()
                interviews = Interview.objects.filter(
                    submission__marketing_team__name=team_name,
                    created__gte=previous_meeting_date
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offers = Project.objects.filter(
                    statuses__status="received",
                    statuses__created__gte=previous_meeting_date,
                    submission__marketing_team__name=team_name,
                ).count()

                text += \
                    f"""| ** {team_name} ** | {interviews} | {offers} | {bench} | {pool} |\n"""

            text += """\n\n
| Team Name | Moved to Marketing |
|:----------|:-------------------|
"""
            teams = Team.objects.filter(dept='Recruitment')
            for team in teams:
                consultant_count = Consultant.objects.filter(
                    pocs__poc__team=team,
                    pocs__poc_type='recruiter',
                    marketing__start__gte=previous_meeting_date,
                ).count()

                text += f"| {team.name.title()} | {consultant_count} |\n"

            data = {
                "response_type": "in_channel",
                "username": "Log1 Updates",
                "text": text,
            }
            # post_msg_using_webhook(config.loud_speakers_url, data)
            return Response({"message": "message sent"}, status=status.HTTP_200_OK)
        return Response({"message": "Previous meeting not found"}, status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @action(methods=['get'], detail=False, url_path='set_meeting')
    def set_meeting(self, request):
        meetings = ScrumMeeting.objects.filter(previous=True)
        for meeting in meetings:
            meeting.previous = False
            meeting.save()
        ScrumMeeting.objects.get_or_create(held_on=datetime.today(), is_previous=True)
        return Response({"message": "success"}, status=status.HTTP_201_CREATED)


# Route - /cmd/
class SlashCommandViewSets(GenericViewSet):
    queryset = User.objects.all()
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
                submission__marketing_team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            offer_count = Project.objects.filter(
                statuses__created__day=day,
                statuses__created__year=year,
                statuses__created__month=month,
                statuses__status__in=['received', 'on_boarded'],
                submission__marketing_team__name__iexact=team.name,
            ).count()
            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__day=day,
                statuses__created__year=year,
                statuses__created__month=month,
                submission__marketing_team__name__iexact=team.name,
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

    @staticmethod
    def team_data_by_start(start, command):
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
                submission__marketing_team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            offer_count = Project.objects.filter(
                statuses__created__gte=start,
                statuses__status__in=['received', 'on_boarded'],
                submission__marketing_team__name__iexact=team.name,

            ).count()
            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__gte=start,
                submission__marketing_team__name__iexact=team.name,
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
                submission__marketing_team__name__iexact=team.name
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()

            offer_count = Project.objects.filter(
                statuses__created__year=year,
                statuses__created__month=month,
                statuses__status__in=['received', 'on_boarded'],
                submission__marketing_team__name__iexact=team.name,
            ).count()

            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__year=year,
                statuses__created__month=month,
                submission__marketing_team__name__iexact=team.name,
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
    def consultant(self, request):
        try:
            api_key = request.GET.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

            query = request.GET.get('text', None)
            command = request.GET.get('command', None)

            if not query and len(query) > 3:
                return Response({"text": f"{command} {query} \n Bad Input"}, status=status.HTTP_200_OK)

            data_type = query.split(" ")[0]
            name = query.split(" ")[1]

            consultants = Consultant.objects.filter(name__istartswith=name).exclude(status='terminated')
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
            write_exception(error, request)
            return Response({"text": "Bad Request", "error": str(error)}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='marketer')
    def marketer(self, request):
        try:
            api_key = request.GET.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

            query = request.GET.get('text', None)
            command = request.GET.get('command', None)
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
            write_exception(error, request)
            return Response({"text": "Bad Request", "error": str(error)}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            api_key = request.GET.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

            query = request.GET.get('text', None)
            command = request.GET.get('command', None)
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
| Name | Email | Phone No | Teams | Status | In Pool | RTG | Marketing Start | Days | Recruiter | Preferred Location |
|:-----|:------|:---------|:------|:-------|:--------|:----|:----------------|:-----|:----------|:-------------------|
"""
                    bench_consultant = Consultant.objects.filter(marketing__status='open').exclude(status='terminated')
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        teams = ", ".join(list(marketing.teams.all().values_list('name', flat=True)))
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        if marketing.start:
                            days = (date.today() - marketing.start).days + marketing.previous_marketing_days
                        else:
                            days = None
                        text += f"| {consultant.name} | {consultant.email} | {consultant.phone_no} | {teams} | {consultant.status} | {marketing.in_pool} | {marketing.rtg} | {str(marketing.start)} | {days} | {recruiter} | {preferred_location} |\n"

                else:
                    text = f"""#### Team Status :memo: \n
Team - {arg2.title()}
command - {slash_command}\n
| Name | Email | Phone No | Status | In Pool | RTG | Marketing Start | Days | Recruiter | Preferred Location |
|:-----|:------|:---------|:-------|:--------|:----|:----------------|:-----|:----------|:-------------------|
"""
                    bench_consultant = Consultant.objects.filter(
                        marketing__status='open',
                        marketing__teams__name__iexact=arg2,
                    ).exclude(status='terminated')
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        days = (
                                       date.today() - marketing.start).days + marketing.previous_marketing_days if marketing.start else None
                        text += f"| {consultant.name} | {consultant.email} | {consultant.phone_no} | {consultant.status} | {marketing.in_pool} | {marketing.rtg} | {str(marketing.start)} | {days} | {recruiter} | {preferred_location} |\n"

            else:
                return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)

            return Response({"text": text}, status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"text": "Bad request", "error": str(error)}, status.HTTP_200_OK)


# Route - /support_report/
class EngineeringReportViewSets(GenericViewSet, ListModelMixin):
    queryset = ProjectSupport.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportDetailSerializer

    @staticmethod
    def get_support_counts(supports):
        counts = dict()
        supports = supports.order_by(
            'project__id', 'project__consultant__id'
        ).distinct('project__id', 'project__consultant__id')
        active = training = less_active = independent = 0
        terminated = supports.filter(project__statuses__status__istartswith='terminated').count()
        supports = supports.filter(end=None).exclude(project__statuses__status__istartswith='terminated')
        total = supports.count()
        for support in supports:
            project = support.project
            if project.start_date and project.start_date > date.today():
                training += 1
            elif project.support.filter(end=None, statuses__frequency__exact='active',
                                        statuses__is_current=True,
                                        project__start_date__lte=date.today()).first():
                active += 1
            elif project.support.filter(end=None, statuses__frequency__exact='less_active',
                                        statuses__is_current=True).first():
                less_active += 1
            elif project.support.filter(end=None, statuses__frequency='independent',
                                        statuses__is_current=True).first():
                independent += 1
        counts['total'] = total
        counts['active'] = active
        counts['training'] = training
        counts['terminated'] = terminated
        counts['less_active'] = less_active
        counts['independent'] = independent
        return counts

    def list(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filter_for = request.GET.get('filter_for', None)
            filter_by_status = request.GET.get('status', None)
            filter_by_tech = request.GET.get('filter_by_tech', None)

            supports = ProjectSupport.objects.all()
            if query:
                query = query.lstrip().replace(':amp:', '&')
                supports = supports.filter(
                    Q(support__employee_name__istartswith=query) |
                    Q(project__consultant__name__istartswith=query) |
                    Q(project__submission__client__istartswith=query) |
                    Q(project__submission__lead__primary_skill__istartswith=query) |
                    Q(project__submission__lead__secondary_skills__istartswith=query)
                )

            if filter_for == 'my':
                supports = supports.filter(support=request.user)

            dev = ['Java', 'Python', 'Aws', 'DevOps', 'Full Stack', 'Nodejs', 'Angular', 'React', 'DA', 'Others']
            ba = ['Salesforce', 'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'BA', 'BI']
            if filter_by_tech == 'ba':
                supports = supports.filter(
                    Q(project__submission__lead__primary_skill__in=ba) |
                    Q(project__submission__lead__secondary_skills__istartswith=ba)
                )
            elif filter_by_tech == 'dev':
                supports = supports.filter(
                    Q(project__submission__lead__primary_skill__in=dev) |
                    Q(project__submission__lead__secondary_skills__istartswith=dev)
                )

            data_count = self.get_support_counts(supports)

            terminated = supports.filter(project__statuses__status__istartswith='terminated')

            supports = supports.filter(end=None).exclude(
                project__statuses__status__istartswith='terminated'
            ).order_by('-project__start_date', '-start')
            data = {
                "total": supports,
                "training": supports.filter(statuses__frequency__exact='active',
                                            statuses__is_current=True, project__start_date__gt=date.today()),
                "active": supports.filter(statuses__frequency__exact='active',
                                          statuses__is_current=True, project__start_date__lte=date.today()),
                "less_active": supports.filter(statuses__frequency__exact='less_active', statuses__is_current=True),
                "independent": supports.filter(statuses__frequency='independent', statuses__is_current=True),
            }
            if filter_by_status != 'terminated':
                supports = data[filter_by_status]
            elif filter_by_status == 'terminated':
                supports = terminated

            page_count = {
                "total": data['total'].count(),
                "active": data["active"].count(),
                "training": data['training'].count(),
                "terminated": terminated.count(),
                "less_active": data["less_active"].count(),
                "independent": data["independent"].count()
            }

            serializer = ProjectSupportDetailSerializer(
                supports.order_by('support__employee_name', '-start')[first:last], many=True)
            return Response({"data": serializer.data, "counts": data_count, "page_count": page_count}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status.HTTP_400_BAD_REQUEST)


# Route - /marketing_report/
class MarketingReportViewSets(GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportDetailSerializer

    @action(methods=['get'], detail=False, url_path='marketer')
    def marketer(self, request):
        try:
            first, last = get_page_limits(request)
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            query = request.GET.get('query', None)
            user_status = request.GET.get('user_status', 'all')
            export = json.loads(request.GET.get('export', 'false'))
            filter_by_team = request.GET.get('filter_by_team', None)

            if query:
                employees = User.objects.filter(employee_name__istartswith=query.lstrip().replace(':amp:', '&'))
            else:
                employees = User.objects.filter(team__dept='Marketing', role__name='marketer')
            if user_status == 'isActive':
                employees = employees.filter(is_active=True, account_login=True)
            elif user_status == 'inActive':
                employees = employees.filter(
                    Q(is_active=True, account_login=False) |
                    Q(is_active=False, account_login=True) |
                    Q(is_active=False, account_login=False)
                )
            if filter_by_team:
                employees = employees.filter(team__name=filter_by_team)
            if start and end and datetime.strptime(start, '%Y-%m-%d').date() > datetime.strptime(end,
                                                                                                 '%Y-%m-%d').date():
                return Response({'message': 'Invalid date filter'}, status.HTTP_400_BAD_REQUEST)
            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today()
            data, url = list(), ""
            total = employees.count()
            if export:
                first, last = 0, len(employees)
            for user in employees[first:last]:
                con_assigned = ", ".join(
                    list(user.marketed.filter(status='open').values_list('consultant__name', flat=True))
                )
                submission_count = Submission.objects.filter(
                    created_by=user, created__gte=start, created__lte=end
                ).exclude(status='cancelled').count()
                unique_interview_count = Interview.objects.filter(
                    submission__created_by=user, created__gte=start, created__lte=end, submission__rank__in=[0, 1]
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                repeat_interview_count = Interview.objects.filter(
                    submission__created_by=user, created__gte=start, created__lte=end, submission__rank__gt=1
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offer_count = Project.objects.filter(
                    statuses__status='received',
                    submission__created_by=user,
                    statuses__created__gte=start, statuses__created__lte=end
                ).count()
                data.append({
                    "id": user.id,
                    "offer": offer_count,
                    "team": user.team.name if user.team else 'NA',
                    "submission": submission_count,
                    "employee_name": user.employee_name,
                    "unique_interview": unique_interview_count,
                    "repeat_interview": repeat_interview_count,
                    "consultant_assigned": con_assigned if len(con_assigned) > 0 else None,
                })
                col_name = [
                    {"name": "employee_name", "display_name": "Employee Name"},
                    {"name": "team", "display_name": "Team Name"},
                    {"name": "submission", "display_name": "Submission"},
                    {"name": "unique_interview", "display_name": "Unique Interview"},
                    {"name": "repeat_interview", "display_name": "Repeat Interview"},
                    {"name": "offer", "display_name": "Offer"},
                    {"name": "consultant_assigned", "display_name": "Consultant Assigned"},
                ]
                if export:
                    url = export_to_csv(
                        data, col_name, f"marketer_{datetime.now().strftime('%d-%B-%Y')}.csv",
                        request, "Marketing Report"
                    )
            return Response({"data": data, "total": total, "file_url": url}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def get_marketing_team_report_data(team, **kwargs):
        try:
            start = kwargs.get('start')
            end = kwargs.get('end')
            team_data = kwargs.get('team_data')
            request = kwargs.get('request')

            bench_consultant = Consultant.objects.filter(
                marketing__teams__in=team, marketing__status='open',
                created__gte=start, created__lte=end
            ).order_by('id').distinct('id')
            submission = Submission.objects.filter(
                marketing_team__in=team,
                created__gte=start, created__lte=end,
            ).exclude(status='draft').order_by('id').distinct('id')
            interview = Interview.objects.filter(
                start_time__gte=start, start_time__lte=end,
                submission__marketing_team__in=team
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id')
            offer = Project.objects.filter(
                submission__marketing_team__in=team,
                created__gte=start, created__lte=end,
            ).order_by('id').distinct('id')
            joining = Project.objects.filter(
                statuses__status='joined',
                submission__marketing_team__in=team,
                statuses__created__gte=start, statuses__created__lte=end,
            ).order_by('id').distinct('id')
            completion = Project.objects.filter(
                statuses__status='complete',
                submission__marketing_team__in=team,
                statuses__created__gte=start, statuses__created__lte=end,
            ).order_by('id').distinct('id')

            termination_type = request.GET.get("termination_type", None)
            termination_mapping = {
                "Resigned": "terminated-resigned",
                "Fired": "terminated-fired",
            }
            is_start_with = termination_mapping.get(termination_type, "terminated")

            if termination_type == "Other":
                termination = Project.objects.filter(
                    statuses__status=is_start_with,
                    submission__marketing_team__in=team,
                    statuses__created__gte=start, statuses__created__lte=end,
                ).order_by('id').distinct('id')
            else:
                termination = Project.objects.filter(
                    statuses__status__istartswith=is_start_with,
                    submission__marketing_team__in=team,
                    statuses__created__gte=start, statuses__created__lte=end,
                ).order_by('id').distinct('id')

            scrum_master = ''
            if team_data:
                scrum_masters = User.objects.filter(team__name__iexact=team[0].name, role__name='admin', is_active=True)
                scrum_master = None
                if scrum_masters:
                    scrum_master = ", ".join(list(scrum_masters.values_list('employee_name', flat=True)))

            team_id = team[0].id if team_data else 0
            team_name = team[0].name if team_data else 'Total'
            scrum_master = scrum_master
            offer_count = offer.count()
            joining_count = joining.count()
            interview_count = interview.count()
            bench_consultant_count = bench_consultant.count()
            submission_count = submission.count()
            completion_count = completion.count()
            termination_count = termination.count()

            team_data = {
                'data': {
                    "id": team_id,
                    "team": team_name,
                    "offer": {'count': offer_count,
                              'data': ReportSerializer(offer[0:3], many=True, context={'model': 'Project'}).data},
                    "scrum_master": scrum_master,
                    "joined": {'count': joining_count,
                               'data': ReportSerializer(joining[0:3], many=True, context={'model': 'Project'}).data},
                    "interview": {'count': interview_count,
                                  'data': ReportSerializer(interview[0:3], many=True,
                                                           context={'model': 'Interview'}).data},
                    "bench_consultant": {'count': bench_consultant_count,
                                         'data': ReportSerializer(bench_consultant[0:3], many=True,
                                                                  context={'model': 'Consultant'}).data},
                    "submission": {'count': submission_count,
                                   'data': ReportSerializer(submission[0:3], many=True,
                                                            context={'model': 'Submission'}).data},
                    "completion": {'count': completion_count,
                                   'data': ReportSerializer(completion[0:3], many=True,
                                                            context={'model': 'Project'}).data},
                    "termination": {'count': termination_count,
                                    'data': ReportSerializer(termination[0:3], many=True,
                                                             context={'model': 'Project'}).data},
                },
                'count': {
                    "id": team_id,
                    "team": team_name,
                    "scrum_master": scrum_master,
                    "offer_count": offer_count,
                    "joined_count": joining_count,
                    "bench_consultant": bench_consultant_count,
                    "interview_count": interview_count,
                    "completion_count": completion_count,
                    "submission_count": submission_count,
                    "termination_count": termination_count,
                }
            }
            return team_data
        except Exception as error:
            write_exception(error, request)
            return {}

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            export = json.loads(request.GET.get('export', 'false'))

            if start and end and datetime.strptime(
                    start, '%Y-%m-%d').date() > datetime.strptime(end, '%Y-%m-%d').date():
                return Response({'message': 'Invalid date filter'}, status.HTTP_400_BAD_REQUEST)

            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today()
            end = end + timedelta(days=1) if type(end) is not str else \
                datetime.strptime(end, '%Y-%m-%d').date() + timedelta(days=1)
            data, url = list(), ""
            teams = Team.objects.filter(dept='Marketing')
            data = []
            export_data = []
            for team in teams:
                team_data = self.get_marketing_team_report_data(team=[team], start=start, end=end, request=request,
                                                                team_data=True)
                data.append(team_data.get('data'))
                export_data.append(team_data.get('count'))

            team_data = self.get_marketing_team_report_data(team=teams, start=start, end=end, request=request,
                                                            team_data=False)
            data.append(team_data.get('data'))
            export_data.append(team_data.get('count'))

            col_name = [
                {"name": "team", "display_name": "Team Name"},
                {"name": "offer_count", "display_name": "Offer Count"},
                {"name": "joined_count", "display_name": "Joined Count"},
                {"name": "scrum_master", "display_name": "Scrum Master"},
                {"name": "interview_count", "display_name": "Interview Count"},
                {"name": "bench_consultant", "display_name": "Bench Consultant"},
                {"name": "submission_count", "display_name": "Submission Count"},
                {"name": "completion_count", "display_name": "completion Count"},
                {"name": "termination_count", "display_name": "termination Count"},
            ]
            if export:
                url = export_to_csv(
                    export_data, col_name, f"team_report_{datetime.now().strftime('%d-%B-%Y')}.csv", request,
                    "Marketing Team Report"
                )
            return Response({"data": data, "file_url": url}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='team_data')
    def team_data(self, request, pk):
        try:
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today()

            submission_count = Submission.objects.filter(
                created_by__team__id=pk,
                created__gte=start, created__lte=end,
            ).exclude(status='draft').order_by('id').distinct('id').count()
            interview_count = Interview.objects.filter(
                created__gte=start, created__lte=end,
                submission__marketing_team__id=pk
            ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
            offer_count = Project.objects.filter(
                submission__marketing_team__id=pk,
                statuses__status__in=['new', 'received', 'on_boarded'],
                statuses__created__gte=start, statuses__created__lte=end,
            ).order_by('id').distinct('id').count()
            joining_count = Project.objects.filter(
                statuses__status='joined',
                submission__marketing_team__id=pk,
                statuses__created__gte=start, statuses__created__lte=end,
            ).order_by('id').distinct('id').count()
            termination_count = Project.objects.filter(
                statuses__status__istartswith='terminated',
                submission__marketing_team__id=pk,
                statuses__created__gte=start, statuses__created__lte=end,
            ).order_by('id').distinct('id').count()

            counts_data = [
                {"display_name": "Submission Count", "count": submission_count, "default": submission_count},
                {"display_name": "Interview Count", "count": interview_count, "default": submission_count},
                {"display_name": "Offer Count", "count": offer_count, "default": submission_count},
                {"display_name": "Joined Count", "count": joining_count, "default": submission_count},
                {"display_name": "Termination Count", "count": termination_count, "default": submission_count}
            ]
            return Response({"data": counts_data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='consultant')
    def consultant(self, request):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            export = json.loads(request.GET.get('export', 'false'))
            filter_by_team = request.GET.get('filter_by_team', None)

            bench_consultant = Consultant.objects.filter(marketing__status='open'). \
                exclude(status='terminated').distinct('id').order_by('id')

            if query:
                bench_consultant = bench_consultant.filter(name__istartswith=query.lstrip().replace(':amp:', '&'))

            if filter_by_team:
                bench_consultant = bench_consultant.filter(marketing__teams__name=filter_by_team,
                                                           marketing__status='open')

            data, url = list(), ""
            total = bench_consultant.count()
            if export:
                first, last = 0, len(bench_consultant)
            for consultant in bench_consultant[first:last]:
                preferred_location = ''
                marketing = consultant.marketing.filter(status='open').first()
                if marketing.preferred_location:
                    preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                teams = ", ".join(list(marketing.teams.all().values_list('name', flat=True)))
                recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                submission_count = Submission.objects.filter(
                    consultant_marketing__consultant=consultant
                ).exclude(status='cancelled').count()
                interview_count = Interview.objects.filter(
                    submission__consultant_marketing__consultant=consultant
                ).exclude(status='cancelled').distinct('submission').order_by().count()
                project_count = Project.objects.filter(consultant=consultant).count()
                days = (
                               date.today() - marketing.start).days + marketing.previous_marketing_days if marketing.start else None
                data.append({
                    'id': consultant.id, 'days': days, 'teams': teams, 'recruiter': recruiter,
                    'submission_count': submission_count, 'preferred_location': preferred_location,
                    'email': consultant.email, 'status': consultant.status, 'project_count': project_count,
                    'phone_no': consultant.phone_no, 'interview_count': interview_count, 'name': consultant.name,
                })
                col_name = [
                    {"name": "name", "display_name": "Name"},
                    {"name": "teams", "display_name": "Teams"},
                    {"name": "days", "display_name": "Days on Bench"},
                    {"name": "submission_count", "display_name": "Submission"},
                    {"name": "interview_count", "display_name": "Interview"},
                    {"name": "project_count", "display_name": "Project"},
                    {"name": "status", "display_name": "Status"},
                ]
                if export:
                    url = export_to_csv(
                        data, col_name, f"consultant_report_{datetime.now().strftime('%d-%B-%Y')}.csv", request,
                        "Marketing Consultant Report"
                    )
            return Response({'data': data, "total": total, "file_url": url}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='supervisor')
    def supervisor(self, request):
        try:
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            query = request.GET.get('query', None)
            user_status = request.GET.get('user_status', 'all')
            export = json.loads(request.GET.get('export', 'false'))

            if start and end and datetime.strptime(start, '%Y-%m-%d').date() > datetime.strptime(end,
                                                                                                 '%Y-%m-%d').date():
                return Response({'message': 'Invalid date filter'}, status.HTTP_400_BAD_REQUEST)
            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today() + timedelta(days=1)

            supervisors = User.objects.filter(role__name='interviewee')
            if user_status == 'isActive':
                supervisors = supervisors.filter(is_active=True, account_login=True)
            elif user_status == 'inActive':
                supervisors = supervisors.filter(
                    Q(is_active=True, account_login=False) |
                    Q(is_active=False, account_login=True) |
                    Q(is_active=False, account_login=False)
                )
            if query:
                supervisors = supervisors.filter(employee_name__istartswith=query.lstrip().replace(':amp:', '&'))
            data = []

            for sup in supervisors:
                interview_count = Interview.objects.filter(supervisor=sup, start_time__gte=start, start_time__lte=end) \
                    .exclude(status__in=['cancelled', 'scheduled', 'rescheduled', 'feedback_due']).count()
                pass_count = Interview.objects.filter(
                    supervisor=sup, start_time__gte=start, start_time__lte=end, status__in=['next_round', 'offer']
                ).count()
                fail_count = Interview.objects.filter(
                    supervisor=sup, start_time__gte=start, start_time__lte=end, status='failed'
                ).count()
                data.append({
                    "id": sup.id, "name": sup.employee_name, "interviews": interview_count, "email": sup.email,
                    "pass": pass_count, "technology": sup.technology, "fail": fail_count,
                    "team": sup.team.name if sup.team else None
                })
            col_name = [
                {"name": "name", "display_name": "Name"},
                {"name": "technology", "display_name": "Technology"},
                {"name": "interviews", "display_name": "Total Interview Rounds"},
                {"name": "pass", "display_name": "Total Passed"},
                {"name": "fail", "display_name": "Total Failed"}
            ]
            url = ""
            if export:
                url = export_to_csv(
                    data, col_name, f"supervisor_report_{datetime.now().strftime('%d-%B-%Y')}.csv", request,
                    "Marketing Supervisor Report"
                )
            return Response({'data': data, "total": supervisors.count(), "file_url": url}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='compare_supervisors')
    def compare_supervisors(self, request):
        try:
            data = []
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            supervisors = json.loads(request.GET.get('supervisors'))

            if start and end and datetime.strptime(start, '%Y-%m-%d').date() > datetime.strptime(end,
                                                                                                 '%Y-%m-%d').date():
                return Response({'message': 'Invalid date filter'}, status.HTTP_400_BAD_REQUEST)
            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today() + timedelta(days=1)

            interviews = Interview.objects.filter(supervisor_id__in=supervisors, start_time__gte=start,
                                                  start_time__lte=end) \
                .exclude(status__in=['cancelled', 'scheduled', 'rescheduled', 'feedback_due']).order_by('-round')
            max_rounds = interviews.first().round if interviews else 0
            for sup_id in supervisors:
                supervisor = get_object_or_404(User, id=sup_id)
                queryset = interviews.filter(supervisor=supervisor).order_by('-round')
                sup_max_rounds = queryset.first().round if queryset else 0
                sup_data = {
                    "id": supervisor.id, "name": supervisor.employee_name, "rounds": []
                }
                for round_number in range(1, sup_max_rounds + 1):
                    pass_interviews = queryset.filter(round=round_number, status__in=['next_round', 'offer']).count()
                    fail_interviews = queryset.filter(round=round_number, status='failed').count()
                    sup_data['rounds'].append({
                        "pass": pass_interviews, "fail": fail_interviews
                    })
                data.append(sup_data)

            return Response({'max_rounds': max_rounds, 'data': data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)


class DetailedReportViewSets(GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='consultant')
    def consultant(self, request):
        try:
            first, last = get_page_limits(request)
            end = request.GET.get('end', None)
            start = request.GET.get('start', None)
            team = request.GET.get('team', None)

            if not start and not end:
                return Response({"message": ERR_DURATION}, status=status.HTTP_400_BAD_REQUEST)

            if team:
                team_obj = get_object_or_404(Team, id=team)
                queryset = Consultant.objects.filter(
                    created__gte=start, created__lte=end, marketing__teams__in=[team_obj], marketing__status='open'
                ).order_by('id').distinct('id')
            else:
                queryset = Consultant.objects.filter(
                    created__gte=start, created__lte=end, marketing__teams__dept='Marketing', marketing__status='open'
                ).order_by('id').distinct('id')

            serializer = ConsultantInfoSerializer(queryset[first: last], many=True)
            return Response({"data": serializer.data, "count": queryset.count()}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='submission')
    def submission(self, request):
        try:
            first, last = get_page_limits(request)
            end = request.GET.get('end', None)
            team = request.GET.get('team', None)
            start = request.GET.get('start', None)

            if not start and not end:
                return Response({"message": ERR_DURATION}, status=status.HTTP_400_BAD_REQUEST)

            queryset = Submission.objects.filter(
                created__gte=start, created__lte=end, marketing_team__dept='Marketing'
            ).exclude(status='draft')

            if team:
                queryset = queryset.filter(marketing_team_id=team).order_by('id').distinct('id')
            else:
                queryset = queryset.order_by('id').distinct('id')

            serializer = SubmissionInfoSerializer(queryset[first: last], many=True)
            return Response({"data": serializer.data, "count": queryset.count()}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='interview')
    def interview(self, request):
        try:
            queryset = []
            first, last = get_page_limits(request)
            end = request.GET.get('end', None)
            team = request.GET.get('team', None)
            start = request.GET.get('start', None)

            if not start and not end:
                return Response({"message": ERR_DURATION}, status=status.HTTP_400_BAD_REQUEST)

            if team:
                sub_ids = Interview.objects.filter(
                    start_time__gte=start, start_time__lte=end, submission__marketing_team_id=team
                ).exclude(status='cancelled'
                          ).order_by('submission_id').distinct('submission_id').values_list('submission_id', flat=True)
            else:
                sub_ids = Interview.objects.filter(
                    start_time__gte=start, start_time__lte=end, submission__marketing_team__dept='Marketing'
                ).exclude(status='cancelled'
                          ).order_by('submission_id').distinct('submission_id').values_list('submission_id', flat=True)

            for sub_id in sub_ids:
                latest_interview = Interview.objects.filter(
                    submission=sub_id).exclude(status='cancelled').order_by('-id').first()
                if latest_interview:
                    queryset.append(latest_interview)

            serializer = InterviewInfoSerializer(queryset[first: last], many=True)
            return Response({"data": serializer.data, "count": len(queryset)}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='purchase_order')
    def purchase_order(self, request):
        try:
            first, last = get_page_limits(request)
            end = request.GET.get('end', None)
            tab = request.GET.get('tab', None)
            team = request.GET.get('team', None)
            start = request.GET.get('start', None)
            termination_type = request.GET.get('type', None)

            if not start and not end:
                return Response({"message": ERR_DURATION}, status=status.HTTP_400_BAD_REQUEST)

            if not tab and tab not in ['Offer', 'Joined', 'Complete', 'Terminated']:
                return Response({"message": "Please provide correct tab name"}, status=status.HTTP_400_BAD_REQUEST)

            if team:
                queryset = Project.objects.filter(submission__marketing_team_id=team)
            else:
                queryset = Project.objects.filter(submission__marketing_team__dept='Marketing')

            if tab == "Offer":
                queryset = queryset.filter(
                    created__gte=start, created__lte=end, statuses__status__in=['new', 'received', 'on_boarded']
                ).order_by('id').distinct('id')

            elif tab == "Joined":
                queryset = queryset.filter(
                    statuses__status='joined', statuses__created__gte=start, statuses__created__lte=end
                ).order_by('id').distinct('id')

            elif tab == "Complete":
                queryset = queryset.filter(
                    statuses__status='complete', statuses__created__gte=start, statuses__created__lte=end
                ).order_by('id').distinct('id')

            elif tab == "Terminated":
                termination_mapping = {
                    'Resigned': 'terminated-resigned',
                    'Fired': 'terminated-fired',
                }
                is_start_with = termination_mapping.get(termination_type, 'terminated')
                if termination_type == "Other":
                    queryset = queryset.filter(
                        statuses__status=is_start_with, statuses__created__gte=start, statuses__created__lte=end
                    ).order_by('id').distinct('id')
                elif termination_type:
                    queryset = queryset.filter(
                        statuses__status__istartswith=is_start_with,
                        statuses__created__gte=start, statuses__created__lte=end
                    ).order_by('id').distinct('id')
                else:
                    queryset = queryset.filter(
                        statuses__status__istartswith='terminated',
                        statuses__created__gte=start, statuses__created__lte=end
                    ).order_by('id').distinct('id')

            serializer = ProjectInfoSerializer(queryset[first: last], many=True)
            return Response({"data": serializer.data, "count": queryset.count()}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)


# Route - /engineers/
class EngineerReportXposedViewSets(GenericViewSet):
    queryset = User.objects.all()
    serializer_class = ProjectSupportDetailSerializer

    @staticmethod
    def verify_api_key(api_key):
        if not APIKey.objects.is_valid(api_key):
            return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return True

    @action(methods=['get'], detail=False, url_path='project/support')
    def get_info(self, request, *args, **kwargs):
        self.verify_api_key(request.GET.get('api_key'))
        try:
            resp = {}
            count = 1
            emp_info = {}
            # cycle_info = request.GET.get('cycle', 1)
            cycle_info = 1
            if request.GET.get('emp_id') is None and request.GET.get('project_id') is None:
                return Response({"message": "Employee ID and project ID does not exist"}, status=status.HTTP_200_OK)
            if request.GET.get('emp_id'):
                try:
                    engineer = User.objects.get(employee_id=request.GET.get('emp_id'))
                    emp_info = {
                        "name": engineer.employee_name, "emp_id": engineer.employee_id, "email": engineer.email
                    }
                except Exception:
                    return Response({"message": "Employee Id does not exist"}, status.HTTP_400_BAD_REQUEST)
            if request.GET.get('project_id'):
                try:
                    project = Project.objects.get(pk=request.GET.get('project_id'))
                except Exception:
                    return Response({"message": "project not found"}, status.HTTP_400_BAD_REQUEST)

            if cycle_info:
                if cycle_info == '1':
                    cycle_duration = 'January to June'
                    cycle_date = datetime.strptime(f"{date.today().year}-01-01", '%Y-%m-%d').date()
                else:
                    cycle_duration = 'July to December'
                    year = date.today().year if date.today().month > 6 else date.today().year - 1
                    cycle_date = datetime.strptime(f"{year}-07-01", '%Y-%m-%d').date()
            else:
                if date.today().month < 7:
                    cycle_duration = 'January to June'
                    cycle_date = datetime.strptime(f"{date.today().year}-01-01", '%Y-%m-%d').date()
                else:
                    cycle_duration = 'July to December'
                    cycle_date = datetime.strptime(f"{date.today().year}-07-01", '%Y-%m-%d').date()

            if request.GET.get('emp_id'):
                supports = ProjectSupport.objects.filter(support=engineer, is_proxy_support=False).filter(
                    Q(end__gt=cycle_date) | Q(end__isnull=True)
                )
            else:
                supports = ProjectSupport.objects.filter(project=project).order_by('-created')

            for support in supports:
                prev_statuses = []
                handover_given = False
                handover_received = False
                project = support.project
                statuses = support.statuses
                training_duration = 0
                support_start = cycle_date if cycle_date > support.start else support.start

                if statuses:
                    active_status_obj = statuses.filter(is_current=True).first()
                    if active_status_obj:
                        active_status = active_status_obj.frequency
                        if active_status == 'handover':
                            handover_given = True
                    else:
                        active_status = "NA"
                else:
                    active_status = "NA"

                prev_supports_qs = ProjectSupport.objects.filter(
                    project=project, start__lt=support.start, is_proxy_support=False
                ).exclude(id=support.id)
                for prev_supports_obj in prev_supports_qs:
                    support_statuses = prev_supports_obj.statuses.filter(is_current=True).values_list('frequency')
                    prev_statuses.extend(support_statuses)

                if 'handover' in prev_statuses:
                    handover_received = True

                technology = project.description.technology if project.description.technology else "NA" \
                    if hasattr(project, 'description') else "NA"

                if support.start < project.start_date and cycle_date < project.start_date:
                    if date.today() < project.start_date:
                        active_status = 'Training'
                        training_duration = (date.today() - support_start).days
                    else:
                        training_duration = (project.start_date - support_start).days
                if support.end:
                    support_duration = f'{(support.end - support_start).days - training_duration} days'
                else:
                    support_duration = f'{(date.today() - support_start).days - training_duration} days'

                resp[f"project_{count}"] = {
                    "status": " ".join(active_status.split('_')).capitalize(),
                    "support_start": support.start, "support_end": support.end,
                    "handover_received": handover_received, "handover_given": handover_given,
                    "is_remote": support.project.is_remote, "client": support.project.submission.client,
                    "support_id": support.id, "skills": technology, "support_duration": 0,
                    "training_duration": f'{training_duration} days', "project_start": project.start_date,
                    "consultant_name": support.project.submission.consultant.name, "project_id": support.project_id
                }
                count += 1
            return Response({"emp_info": emp_info, "cycle_duration": cycle_duration, "data": resp}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='okr/send_mail')
    def okr_send_mail(self, request, *args, **kwargs):
        self.verify_api_key(request.data.get('api_key'))
        try:
            mail_data = {
                'bcc': request.data.get('bcc', []),
                'cc': request.data.get('cc', []),
                'to': request.data.get('to', []),
                'subject': request.data.get('subject', None),
                'body': request.data.get('body', None),
                'from': request.data.get('from', None),
                'template': '../templates/okr_mail_template.html',
                'context': {
                    'employee_name': request.data.get('employee_name', None),
                    'employee_id': request.data.get('employee_id', None),
                    'password': request.data.get('password', None),
                    'url': config.OKR_URL
                },
            }

            required_keys = ['to', 'subject', 'body', 'from']

            for key in required_keys:
                if not mail_data[key]:
                    return Response({"message": f"Key '{key}' is missing or empty."}, status.HTTP_400_BAD_REQUEST)

            try:
                send_email(mail_data, request.data.get('from', 'product@consultadd.com'), None)
            except Exception as e:
                return Response({"message": ERROR_MSG, "error": str(e)}, status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Mail sent successfully"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='timesheet/project')
    def timesheet_project(self, request, *args, **kwargs):
        try:
            self.verify_api_key(request.GET.get('api_key'))
            months = request.GET.get('month', None)
            project_type = request.GET.get('project_type')
            project_id = request.GET.get('project_id', None)
            employee_id = request.GET.get('employee_id', None)
            if project_type == 'support':
                if project_id:
                    project_support = ProjectSupport.objects.filter(project__id=project_id)
                    project_ids = set(project_support.values_list('project__id', flat=True))
                elif months and employee_id:
                    support_ids = []
                    months = months.split(",")
                    for month in months:
                        month = int(month)
                        current_date = datetime.now()
                        first_date_next_month = datetime(
                            current_date.year + 1 if month == 12 else current_date.year, month % 12 + 1, 1)
                        last_date_prev_month = datetime(
                            current_date.year, 12 if month % 12 == 0 else month % 12, 1) - timedelta(days=1)
                        queryset = ProjectSupport.objects.filter(
                            support__employee_id=employee_id, statuses__frequency__in=['active', 'less_active']
                        ).filter(
                            Q(start__lt=last_date_prev_month, end__gt=last_date_prev_month) | Q(end=None)
                        ).exclude(start__gte=first_date_next_month)
                        support_ids.append(queryset.values_list('project__id', flat=True))
                    project_ids = set(support_ids)
                else:
                    project_support = ProjectSupport.objects.filter(
                        statuses__frequency__in=['active', 'less_active'],
                        statuses__is_current=True, support__employee_id=employee_id
                    )
                    project_ids = set(project_support.values_list('project__id', flat=True))
                project = Project.objects.filter(id__in=project_ids)
            elif project_type == 'remote':
                if project_id:
                    project = Project.objects.filter(id=project_id).order_by('id').distinct('id')
                else:
                    try:
                        user = get_object_or_404(User, employee_id=employee_id)
                        consultant = get_object_or_404(Consultant, email=user.email)
                    except ObjectDoesNotExist:
                        return Response({"message": 'No Consultant found'}, status=status.HTTP_400_BAD_REQUEST)
                    project = Project.objects.filter(consultant=consultant, statuses__status__in=['joined', 'extended'],
                                                     statuses__is_current=True).order_by('id').distinct('id')
            else:
                return Response({'message': 'Project Type is required'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = TimesheetProjectSerializer(project, many=True, context={'project_type': project_type})
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='timesheet/test')
    def timesheet_test(self, request, *args, **kwargs):
        try:
            self.verify_api_key(request.GET.get('api_key'))
            submit_date = request.GET.get('submit_date', None)
            test_id = request.GET.get('test_id', None)
            submit_month = request.GET.get('submit_month', None)
            employee_id = request.GET.get('employee_id', None)
            if test_id:
                test = Test.objects.filter(id=test_id)
            else:
                test = Test.objects.filter(status__in=['feedback_due', 'passed', 'failed'])

            if employee_id:
                test = test.filter(engineer__employee_id=employee_id)
            if submit_date:
                test = test.filter(submit_date__date=submit_date)
            if submit_month:
                year, month = submit_month.split('-')
                test = test.filter(submit_date__year=year, submit_date__month=month)
            serializer = TimesheetTestSerializer(test, many=True)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='timesheet/users')
    def timesheet_users(self, request, *args, **kwargs):
        try:
            self.verify_api_key(request.GET.get('api_key'))
            users = User.objects.filter(team__dept='Engineering')
            serializer = TimesheetUserSerializer(users, many=True)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)

    @action(methods=['put'], detail=True, url_path='remote_project/update')
    def project_update(self, request, pk):
        try:
            self.verify_api_key(request.GET.get('api_key'))
            data = copy.copy(request.data)
            user = User.objects.get(employee_id=9998)
            data['update_by'] = user.id
            data['project'] = pk
            serializer = ProjectUpdateSerializer(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            update = ProjectUpdate.objects.get(id=serializer.data['id'])
            for file in request.FILES.getlist('files'):
                file_data = {
                    "file": file,
                    "object_id": update.id,
                    "creator": user,
                    "model": "projectupdate",
                    "type": 'project_update',
                }
                create_attachment(file_data)

            tags = request.data.get('tagged_user', None)
            if tags:
                tag_and_notify(update, tags, user, 'create')

            # Activity
            desc = f"{user.employee_name} added project Update-{update.id}"
            create_activity(data['project'], 'projectupdate', user, desc, 'created')
            return Response({"message": "Project Update is added successfully"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
