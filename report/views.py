from datetime import datetime, date

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config
from employee.models import Team
from project.models import Project
from marketing.models import Interview
from utils_app.models import ScrumMeeting
from consultant.models import ConsultantMarketing
from utils_app.utils import post_msg_using_webhook


class ScrumMeetingReport(GenericViewSet):
    queryset = ScrumMeeting.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='scrum_meeting')
    def scrum_meeting(self, request):
        scrum_meeting = ScrumMeeting.objects.filter(previous=True)
        if scrum_meeting:
            previous_meeting_date = scrum_meeting.first().held_on
            teams = Team.objects.exclude(name__in=['Garuda', 'Flash', 'X+', 'Consultadd', 'Okyte'])
            text = f"""
#### Scrum Report ({str(previous_meeting_date)} - {str(date.today())}) :chart_with_upwards_trend:\n
| Team | Interviews | Offers | Bench | Pool |
|:-----|:-----------|:-------|:------|:-----|
"""
            for team in teams:
                team_name = team.name
                pool = ConsultantMarketing.objects.filter(
                    teams__name=team_name, in_pool=True,
                    status='open').distinct('consultant').order_by().count()
                bench = ConsultantMarketing.objects.filter(
                    teams__name=team_name, in_pool=False,
                    status='open').distinct('consultant').order_by().count()
                interviews = Interview.objects.filter(
                    submission__created_by__team__name=team_name,
                    created__gte=previous_meeting_date
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offers = Project.objects.filter(
                    submission__lead__marketer__team__name=team_name,
                    created__gte=previous_meeting_date).count()

                text += \
                    f"""| ** {team_name} ** | {interviews} | {offers} | {bench} | {pool} |\n"""

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
