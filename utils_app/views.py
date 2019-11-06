from datetime import date, timedelta
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from utils_app.models import City


class CityViewSets(viewsets.ModelViewSet):
    queryset = City.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        return Response({"results": "Method \"GET\" not allowed."}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)
        if query:
            city = City.objects.filter(name__istartswith=query)
        else:
            city = City.objects.all()
        data = city[:20].values('id', 'name', 'state')
        return Response({"results": data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        return Response({"results": "Method \"POST\" not allowed."}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        return Response({"results": "Method \"PUT\" not allowed."}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"results": "Method \"DELETE\" not allowed."}, status=status.HTTP_400_BAD_REQUEST)


def get_time_filter(queryset, filter_by):
    if filter_by == 'today':
        queryset = queryset.filter(created__gte=date.today())

    elif filter_by == 'last_day':
        today = date.today()
        day = date.today().weekday()
        if day == 0:
            last_day = today - timedelta(days=3)
        else:
            last_day = today - timedelta(days=1)
        queryset = queryset.filter(created__gte=last_day)

    elif filter_by == 'week':
        today = date.today()
        start_of_week = today - timedelta(today.weekday())
        queryset = queryset.filter(created__gte=start_of_week)

    elif filter_by == 'last_month':
        last = date.today().replace(day=1) - timedelta(days=1)
        first = last.replace(day=1)
        queryset = queryset.filter(created__range=[first, last])

    elif filter_by == 'this_month':
        first = date.today().replace(day=1)
        last = date.today()
        queryset = queryset.filter(created__range=[first, last])

    return queryset
