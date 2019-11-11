from datetime import date, timedelta
from rest_framework import status, viewsets
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
