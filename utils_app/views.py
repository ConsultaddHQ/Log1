from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin

from django.contrib.contenttypes.models import ContentType

from log1.utils import write_exception
from utils_app.models import City, Choice
from utils_app.serializers import UtilSerializer


class CityViewSets(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('query', '').lstrip().replace(':amp:', '&')
            city = City.objects.filter(name__istartswith=query)
            data = city[:40].values('id', 'name', 'state')
            return Response({"results": data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name='CityViewSets', function_name='list')
            return Response({"error": str(error)}, status=400)


class ChoiceViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = Choice.objects.all()
    serializer_class = UtilSerializer
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
            return Response({"results": data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name='ChoiceViewSet', function_name='list')
            return Response({"error": str(error)}, status=400)

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
            return Response({'results': 'created'}, status=201)
        except Exception as error:
            write_exception(message=error, class_name='ChoiceViewSet', function_name='create')
            return Response({"error": error}, status=400)
