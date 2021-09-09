import json
from datetime import date
from django.db.models import Q

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from project.models import Project
from marketing.utils import date_filter
from engineering.serializers import ProjectSupportSerializer
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from engineering.serializers import EngineeringSerializer, EngineeringDetailSerializer


class EngineeringViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Project.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = EngineeringSerializer

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', None)
            filter_for = request.GET.get('filter_for', 'all')
            filter_json = request.GET.get('filter_json', None)
            first, last = get_page_limits(request)

            projects = Project.objects.filter(
                statuses__is_current=True, statuses__status__in=['new', 'received', 'on_boarded', 'joined'],
            )
            if filter_json:
                filters = json.loads(filter_json)

                if 'project_status' in filters:
                    if filters['project_status'] in ['terminated', 'cancelled']:
                        projects = Project.objects.filter(
                            statuses__is_current=True,
                            statuses__status__istartswith=filters['project_status'],
                        )
                    else:
                        projects = projects.filter(
                            statuses__is_current=True,
                            statuses__status__istartswith=filters['project_status'],
                        )

                if 'assignment' in filters:
                    if filters['assignment'] == 'assigned':
                        projects = projects.exclude(support__end=None)
                    if filters['assignment'] == 'unassigned':
                        projects = projects.filter(support__end=None)

                if 'client' in filters:
                    projects = projects.filter(submission__client=filters['client'])

                if 'support_status' in filters:
                    if filters['support_status'] == 'training':
                        projects = projects.filter(
                            start_date__gt=date.today(),
                            statuses__statuses__is_current=True,
                            statuses__statuses__frequency='more_than_2_days',
                        )
                    elif filters['support_status'] == 'active':
                        projects = projects.filter(
                            start_date__lte=date.today(),
                            statuses__statuses__is_current=True,
                            statuses__statuses__frequency='more_than_2_days',
                        )
                    elif filters['support_status'] == 'less_active':
                        projects = projects.filter(
                            statuses__statuses__is_current=True,
                            statuses__statuses__frequency='less_than_3_days',
                        )
                    elif filters['support_status'] == 'independent':
                        projects = projects.filter(
                            statuses__statuses__is_current=True,
                            statuses__statuses__frequency__in=['independent', 'twice_a_month'],
                        )

                if 'support' in filters:
                    projects = projects.filter(support__support_id=filters['support'])

                start_date = filters.get('start_date', None)
                projects = date_filter(projects, start_date, 'start_date')

            if filter_for == 'my':
                projects = projects.filter(
                    support__support=request.user,
                )

            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(submission__client__istartswith=query) |
                    Q(support__support__employee_name__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            serializer = self.serializer_class(projects[first:last], many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            qs = Project.objects.filter(id=kwargs.get('pk', None))
            if qs:
                serializer = EngineeringDetailSerializer(qs.first())
                return Response({"data": serializer.data}, status=200)
            return Response({"message": "Project not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path="filters")
    def filters(self, request, *args, **kwargs):
        try:
            project_status = [
                {'name': 'new', 'display_name': 'New'},
                {'name': 'received', 'display_name': 'Received'},
                {'name': 'on_boarded', 'display_name': 'On Boarded'},
                {'name': 'joined', 'display_name': 'Joined'},
                {'name': 'complete', 'display_name': 'Complete'},
                {'name': 'cancelled', 'display_name': 'Cancelled'},
                {'name': 'terminated', 'display_name': 'Terminated'},
            ]
            support_status = [
                {'name': 'training', 'display_name': 'Training'},
                {'name': 'active', 'display_name': 'Active'},
                {'name': 'less_active', 'display_name': 'Less Active'},
                {'name': 'independent', 'display_name': 'Independent'},
            ]
            data = {
                "project_status": project_status,
                "support_status": support_status,
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path="support")
    def support(self, request, *args, **kwargs):
        try:
            qs = Project.objects.filter(id=kwargs.get('pk', None))
            if qs:
                serializer = ProjectSupportSerializer(qs.first().support.all().order_by('-created'), many=True)
                return Response({"data": serializer.data}, status=200)
            return Response({"message": "Project not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)
