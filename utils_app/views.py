import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City
from api_key.models import APIKey

logger = logging.getLogger(__name__)


class CityViewSets(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query')
        city = City.objects.filter(name__istartswith=query)
        data = city[:40].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)


class WebHookViewSet(GenericViewSet):
    queryset = City.objects.all()

    @action(methods=["post"], detail=False, url_path='hubspot')
    def hubspot(self, request):
        api_key = request.query_params.get('api_key', None)
        if not APIKey.objects.is_valid(api_key):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        f = open('sample.json', 'w')
        f.write(str(request.data))
        f.write("\n")
        f.write(str(request.method))
        return Response({"result": "ok"}, status=status.HTTP_200_OK)


str = [{'objectId': 6401, 'propertyName': 'candidate_rate', 'propertyValue': '50', 'changeSource': 'CRM_UI',
  'eventId': 3641899323, 'subscriptionId': 240950, 'portalId': 5573564, 'appId': 221149, 'occurredAt': 1591901997558,
  'subscriptionType': 'contact.propertyChange', 'attemptNumber': 0}]
