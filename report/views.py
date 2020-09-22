from datetime import datetime, date, timedelta

from django.db import transaction
from django.db.models import Q
from rest_framework.mixins import *
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config
from api_key.models import APIKey
from employee.models import Team, User
from utils_app.models import ScrumMeeting
from employee.serializers import UserSerializer
from project.models import Project, ProjectSupport
from utils_app.utils import post_msg_using_webhook
from marketing.models import Submission, Interview
from consultant.models import ConsultantMarketing, Consultant
from project.serializers import ProjectSupportDetailSerializer


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
                    submission__created_by__team__name=team_name,
                    created__gte=previous_meeting_date
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offers = Project.objects.filter(
                    statuses__status="received",
                    statuses__created__gte=previous_meeting_date,
                    submission__created_by__team__name=team_name,
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
            post_msg_using_webhook(config.loud_speakers_url, data)
            return Response({"results": "message sent"}, status=status.HTTP_200_OK)
        return Response({"results": "Previous meeting not found"}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @action(methods=['get'], detail=False, url_path='set_meeting')
    def set_meeting(self, request):
        meetings = ScrumMeeting.objects.filter(previous=True)
        for meeting in meetings:
            meeting.previous = False
            meeting.save()
        ScrumMeeting.objects.get_or_create(held_on=datetime.today(), is_previous=True)
        return Response({"results": "success"}, status=status.HTTP_201_CREATED)


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
            api_key = request.query_params.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

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
            return Response({"text": "Bad Request", "error": str(error)}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='marketer')
    def marketer(self, request):
        try:
            api_key = request.query_params.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

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
            return Response({"text": "Bad Request", "error": str(error)}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            api_key = request.query_params.get('api_key', None)
            if not APIKey.objects.is_valid(api_key):
                return Response({"text": "Unauthorized"}, status=status.HTTP_200_OK)

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
| Name | Email | Phone No | Teams | Status | In Pool | RTG | Marketing Start | Days | Recruiter | Preferred Location |
|:-----|:------|:---------|:------|:-------|:--------|:----|:----------------|:-----|:----------|:-------------------|
"""
                    bench_consultant = Consultant.objects.filter(marketing__status='open').exclude(status='archived')
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        teams = ", ".join(list(marketing.teams.all().values_list('name', flat=True)))
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        days = (date.today() - marketing.start).days + marketing.previous_marketing_days if marketing.start else None
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
                    ).exclude(status='archived')
                    for consultant in bench_consultant:
                        marketing = consultant.marketing.filter(status='open').first()
                        preferred_location = marketing.preferred_location.replace('\r\n', ', ')
                        recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                        days = (date.today() - marketing.start).days + marketing.previous_marketing_days if marketing.start else None
                        text += f"| {consultant.name} | {consultant.email} | {consultant.phone_no} | {consultant.status} | {marketing.in_pool} | {marketing.rtg} | {str(marketing.start)} | {days} | {recruiter} | {preferred_location} |\n"

            else:
                return Response({"text": f"{slash_command} \n Bad Input"}, status=status.HTTP_200_OK)

            return Response({"text": text}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"text": "Bad request", "error": str(error)}, status=status.HTTP_200_OK)


class EngineeringReportViewSets(GenericViewSet, ListModelMixin):
    queryset = ProjectSupport.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportDetailSerializer

    @staticmethod
    def get_support_counts(supports):
        supports = supports.order_by('project__id',
                                     'project__consultant__id'
                                     ).distinct('project__id', 'project__consultant__id')
        counts = dict()
        active = training = less_active = independent = 0
        terminated = supports.filter(project__statuses__status__istartswith='terminated').count()
        supports = supports.filter(end=None).exclude(project__statuses__status__istartswith='terminated')
        total = supports.count()
        for support in supports:
            project = support.project
            if project.start_date and project.start_date > date.today():
                training += 1
            elif project.support.filter(end=None, statuses__frequency__exact='more_than_2_days', statuses__is_current=True,
                                        project__start_date__lte=date.today()).first():
                active += 1
            elif project.support.filter(end=None, statuses__frequency__exact='less_than_3_days', statuses__is_current=True).first():
                less_active += 1
            elif project.support.filter(end=None, statuses__frequency__in=('twice_a_month', 'independent'),
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
            query = request.query_params.get('query', None)
            filter_for = request.query_params.get('filter_for', None)
            filter_by_status = request.query_params.get('status', None)
            filter_by_tech = request.query_params.get('filter_by_tech', None)

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
            last, first = page * page_size, page * page_size - page_size

            supports = ProjectSupport.objects.all().order_by('-project__start_date', '-start')
            if query:
                query = query.strip()
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

            terminated = supports.filter(project__statuses__status__istartswith='terminated', is_primary=True)

            supports = supports.filter(end=None).exclude(
                project__statuses__status__istartswith='terminated'
            ).order_by('-project__start_date', '-start')
            data = {
                "total": supports,
                "training": supports.filter(statuses__frequency__exact='more_than_2_days',
                                            statuses__is_current=True, project__start_date__gt=date.today()),
                "active": supports.filter(statuses__frequency__exact='more_than_2_days',
                                          statuses__is_current=True, project__start_date__lte=date.today()),
                "less_active": supports.filter(statuses__frequency__exact='less_than_3_days',
                                               statuses__is_current=True),
                "independent": supports.filter(statuses__frequency__in=('twice_a_month', 'independent'),
                                               statuses__is_current=True),
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

            serializer = ProjectSupportDetailSerializer(supports[first:last], many=True)
            return Response({"results": serializer.data, "counts": data_count, "page_count": page_count}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)


class MarketingReportViewSets(GenericViewSet):
    queryset = Consultant.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportDetailSerializer

    @action(methods=['get'], detail=False, url_path='marketer')
    def marketer(self, request):
        try:
            query = request.query_params.get('query', None)
            start = request.query_params.get('start', None)
            end = request.query_params.get('end', None)
            employees = User.objects.filter(team__dept='Marketing', is_active=True)
            if query:
                query.strip()
                employees = employees.filter(employee_name__istartswith=query)

            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today()

            data = list()
            for user in employees:
                payload = dict()
                con_assigned = ", ".join(
                    list(user.marketed.filter(status='open').values_list('consultant__name', flat=True)))
                submission_count = Submission.objects.filter(
                    created_by=user, created__gte=start, created__lte=end
                ).exclude(status='cancelled').count()
                interview_count = Interview.objects.filter(
                    submission__created_by=user, created__gte=start, created__lte=end
                ).exclude(status='cancelled').count()
                offer_count = Project.objects.filter(
                    statuses__status='received',
                    submission__created_by=user,
                    statuses__created__gte=start, statuses__created__lte=end
                ).count()
                consultant_assigned = con_assigned if len(con_assigned) > 0 else None
                payload["employee_name"] = user.employee_name
                payload["team"] = user.team.name
                payload["submission"] = submission_count
                payload["interview"] = interview_count
                payload["offer"] = offer_count
                payload["consultant_assigned"] = consultant_assigned
                data.append(payload)
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            query = request.query_params.get('query', None)
            start = request.query_params.get('start', None)
            end = request.query_params.get('end', None)

            if not start:
                start = date.today() - timedelta(days=30)
            if not end:
                end = date.today()

            data = list()
            teams = Team.objects.filter(dept='Marketing')
            for team in teams:
                payload = dict()
                bench_consultant = Consultant.objects.filter(
                    marketing__teams__name__iexact=team.name,
                    marketing__status='open'
                ).count()
                submission_count = Submission.objects.filter(
                    created__gte=start, created__lte=end,
                    created_by__team__name__iexact=team.name
                ).exclude(status='draft').count()
                interview_count = Interview.objects.filter(
                    created__gte=start, created__lte=end,
                    submission__created_by__team__name__iexact=team.name
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offer_count = Project.objects.filter(
                    statuses__created__gte=start, statuses__created__lte=end,
                    statuses__status__in=['received', 'on_boarded'],
                    submission__created_by__team__name__iexact=team.name,

                ).count()
                joined_count = Project.objects.filter(
                    statuses__status='joined',
                    statuses__created__gte=start, statuses__created__lte=end,
                    submission__created_by__team__name__iexact=team.name,
                ).count()
                scrum_masters = User.objects.filter(team__name__iexact=team.name, role__name='admin', is_active=True)
                scrum_master = None
                if scrum_masters:
                    scrum_master = ", ".join(list(scrum_masters.values_list('employee_name', flat=True)))

                payload["team"] = team.name.title()
                payload["scrum_master"] = scrum_master
                payload["bench_consultant"] = bench_consultant
                payload["submission_count"] = submission_count
                payload["interview_count"] = interview_count
                payload["offer_count"] = offer_count
                payload["joined_count"] = joined_count
                data.append(payload)

            bench_consultant = Consultant.objects.filter(marketing__status='open').count()
            submission_count = Submission.objects.filter(created__gte=start, created__lte=end).exclude(status='draft').count()
            interview_count = Interview.objects.filter(
                created__gte=start, created__lte=end).exclude(status='cancelled').order_by('submission_id').distinct(
                'submission_id').count()
            offer_count = Project.objects.filter(
                statuses__status__in=['received', 'on_boarded'], statuses__created__gte=start,
                statuses__created__lte=end
            ).count()
            joined_count = Project.objects.filter(
                statuses__status='joined',
                statuses__created__gte=start,  statuses__created__lte=end
            ).count()
            total_count = {
                "bench_consultant": bench_consultant,
                "submission_count": submission_count,
                "interview_count": interview_count,
                "offer_count": offer_count,
                "joined_count": joined_count,

            }
            return Response({"results": data, "total_count": total_count}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='consultant')
    def consultant(self, request):
        try:
            query = request.query_params.get('query', None)
            filter_by_team = request.query_params.get('filter_by_team', None)
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            last, first = page * page_size, page * page_size - page_size
            data = []
            bench_consultant = Consultant.objects.all().exclude(status__in=['archived', 'terminated'])
            if query:
                query = query.strip()
                bench_consultant = bench_consultant.filter(name__istartswith=query)

            if filter_by_team:
                bench_consultant = bench_consultant.filter(marketing__teams__name__iexact=filter_by_team)

            for consultant in bench_consultant:
                obj = dict()
                marketing = consultant.marketing.filter(status='open').first()
                preferred_location = marketing.preferred_location.replace('\r\n', ', ') if marketing else None
                teams = ", ".join(list(marketing.teams.all().values_list('name', flat=True))) if marketing else 'Consultadd'
                recruiter = consultant.recruiter.employee_name if consultant.recruiter else None
                submission_count = Submission.objects.filter(consultant_marketing__consultant=consultant).exclude(
                    status='cancelled').count()
                interview_count = Interview.objects.filter(
                    submission__consultant_marketing__consultant=consultant
                ).exclude(status='cancelled').distinct('submission').order_by().count()
                project_count = Project.objects.filter(consultant=consultant).count()
                days = (date.today() - marketing.start).days + marketing.previous_marketing_days if marketing and marketing.start else None

                obj['days'] = days
                obj['teams'] = teams
                obj['recruiter'] = recruiter
                obj['name'] = consultant.name
                obj['email'] = consultant.email
                obj['status'] = consultant.status
                obj['project_count'] = project_count
                obj['phone_no'] = consultant.phone_no
                obj['interview_count'] = interview_count
                obj['submission_count'] = submission_count
                obj['preferred_location'] = preferred_location
                obj['rtg'] = marketing.rtg if marketing else None
                obj['in_pool'] = marketing.in_pool if marketing else None
                obj['start'] = str(marketing.start) if marketing else None
                data.append(obj)
            return Response({'results': data[first:last]}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
