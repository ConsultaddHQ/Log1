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
