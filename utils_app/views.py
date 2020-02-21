import json
import logging
import requests
from datetime import datetime, date, timedelta

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from constance import config
from utils_app.models import City
from employee.models import User, Team
from utils_app.models import City, ScrumMeeting
from employee.serializers import UserSerializer
from marketing.models import Submission, Interview
from project.models import Project, PROJECT_STATUS_CHOICES
from consultant.models import Consultant, ConsultantMarketing

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
        city = City.objects.filter(name__icontains=query)
        data = city[:20].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)


class UtilsViewSets(GenericViewSet):
    queryset = City.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    @action(methods=['get'], detail=False, url_path='project/statuses')
    def project_statuses(self, request):
        data = [{"name": x} for x, y in PROJECT_STATUS_CHOICES if x not in ['offer', 'paper_work', 'cancelled']]
        return Response({"results": data}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='sm_report')
    def sm_report(self, request):
        scrum_meeting = ScrumMeeting.objects.filter(previous=True)
        if scrum_meeting:
            previous_meeting_date = scrum_meeting.first().held_on
            teams = Team.objects.filter(dept='Marketing')
            text = f"""
#### Scrum Report ({str(previous_meeting_date)} - {str(date.today())}) :chart_with_upwards_trend:\n
| Team | Interviews | Offers | Bench | Pool |
|:-----|:-----------|:-------|:------|:-----|
"""
            for team in teams:
                team_name = team.name
                pool = ConsultantMarketing.objects.filter(
                    is_current=True, end=None,
                    teams__name=team_name, in_pool=True,
                    status='open'
                ).count()
                bench = ConsultantMarketing.objects.filter(
                    is_current=True, end=None,
                    teams__name=team_name, in_pool=False,
                    status='open'
                ).count()
                interviews = Interview.objects.filter(
                    submission__created_by__team__name=team_name,
                    created__gte=previous_meeting_date
                ).exclude(status='cancelled').order_by('submission_id').distinct('submission_id').count()
                offers = Project.objects.filter(
                    submission__lead__marketer__team__name=team_name,
                    created__gte=previous_meeting_date
                ).count()

                text += \
                    f"""| ** {team_name} ** | {interviews} | {offers} | {bench} | {pool} |\n"""

            data = {
                "response_type": "in_channel",
                "username": "Log1 Updates",
                "text": text,
            }
            mattermost_webhook(config.loud_speakers_url, data)
            return Response({"results": "message sent"}, status=status.HTTP_200_OK)
        return Response({"results": "Previous meeting not found"}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @action(methods=['get'], detail=False, url_path='set_meeting')
    def set_meeting(self, request):
        meetings = ScrumMeeting.objects.filter(previous=True)
        meetings.update(previous=False)
        ScrumMeeting.objects.get_or_create(held_on=datetime.today(), previous=True)
        return Response({"results": "success"}, status=status.HTTP_201_CREATED)
