from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin

from django.contrib.contenttypes.models import ContentType

from utils_app.models import City, Choice
from log1.utils import write_exception, ERROR_MSG


class UtilSerializer(serializers.Serializer):
    name = serializers.CharField()


# Route - /city/
class CityViewSet(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', '').lstrip().replace(':amp:', '&')
            city = City.objects.filter(name__istartswith=query)
            data = city[:15].values('id', 'name', 'state', 'country')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /choice/
class ChoiceViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = Choice.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            field = request.GET.get('field')
            model = request.GET.get('model', None)
            queryset = self.queryset.filter(field=field)
            if model:
                content_type = ContentType.objects.get(model=model)
                queryset = queryset.filter(content_type=content_type)
            data = queryset.values('id', 'name', 'display_name', 'field', 'content_type__model')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

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
            return Response({'message': 'Choice Created'}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": error}, status=400)


# Route - /util/
class TeamsTargetViewSet(CreateModelMixin, GenericViewSet):
    queryset = City.objects.all()
    serializer_class = UtilSerializer

    def create(self, request, *args, **kwargs):
        try:
            api_key = request.query_params.get('api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=401)

            prefix, _, _ = api_key.partition(".")
            if prefix != "ypY83gkC":
                return Response({"message": "Unauthorized"}, status=401)

            return Response({"data": "data"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /utility/
class UtilityViewSet(CreateModelMixin, GenericViewSet):
    queryset = City.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='technology')
    def technology(self, request):
        try:
            data = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps', 'BA', 'DA',
                    'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce', 'Cyber Security', 'Other']
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
