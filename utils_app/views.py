import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City

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
