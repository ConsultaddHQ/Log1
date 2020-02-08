from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City


class CityViewSets(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query')
        city = City.objects.filter(name__icontains=query)
        data = city[:20].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)
