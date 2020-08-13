import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from django.contrib.contenttypes.models import ContentType

from utils_app.models import City, Choice

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


class ChoiceViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = Choice.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            field = request.query_params.get('field')
            model = request.query_params.get('model', None)
            queryset = self.queryset.filter(field=field)
            if model:
                content_type = ContentType.objects.get(model=model)
                queryset = queryset.filter(content_type=content_type)
            data = queryset.values('id', 'name', 'display_name', 'field', 'content_type__model')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            model = request.data.get('model', None)
            if model:
                model = ContentType.objects.get(model=model)
            Choice.objects.create(
                content_type=model,
                name=request.data.get('name'),
                field=request.data.get('field'),
                display_name=request.data.get('display_name'),
            )
            return Response({'results': 'created'}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
