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
from utils_app.swagger import list_choice, create_choice, create_util, utility_get_technology, utility_add_technology, \
    list_city, city_country


class UtilSerializer(serializers.Serializer):
    name = serializers.CharField()


# Route - /city/
class CityViewSet(ListModelMixin, GenericViewSet):
    queryset = City.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @list_city
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.queryset
            query = request.query_params.get('query', None)
            country = request.query_params.get('country', '')
            if country:
                queryset = queryset.filter(country=country)
            if query:
                queryset = queryset.filter(name__istartswith=query)
            data = queryset[0:30].values('id', 'name', 'state', 'country')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @city_country
    @action(methods=['get'], detail=False, url_path='country')
    def country(self, request):
        try:
            city = request.GET.get('city', None)
            if city:
                location = city.split(',')
                city = City.objects.filter(name=location[0], state=location[1])
                country = city.first().country if city else None
                return Response({"data": country}, status=200)
            return Response({"data": "No Country Found"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /choice/
class ChoiceViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = Choice.objects.all()
    serializer_class = UtilSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @list_choice
    def list(self, request, *args, **kwargs):
        try:
            field = request.GET.get('field', None)
            model = request.GET.get('model', None)
            queryset = self.queryset.filter(field=field) if field else self.queryset
            if model:
                content_type = ContentType.objects.get(model=model)
                queryset = queryset.filter(content_type=content_type)
            data = queryset.values('id', 'name', 'display_name', 'field', 'content_type__model')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @create_choice
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

    @create_util
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

    @utility_get_technology
    @action(methods=['get'], detail=False, url_path='technology')
    def technology(self, request):
        try:
            choices = Choice.objects.filter(field='technology', content_type__model='user').values('name')
            technologies = [choice['name'] for choice in choices]
            technologies.append('Other')
            return Response({"data": technologies}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @utility_add_technology
    @action(methods=['put'], detail=False, url_path='add_technology')
    def add_technology(self, request):
        try:
            technologies = request.data['technology']
            content_type = ContentType.objects.get(model='user')
            for technology in technologies:
                available_technology = Choice.objects.filter(
                    field='technology', content_type=content_type, name__iexact=technology
                )
                if not available_technology:
                    Choice.objects.create(
                        field='technology', content_type=content_type,
                        display_name=technology, name=technology
                    )
            return Response({"message": "updated technologies"}, status=202)

        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
