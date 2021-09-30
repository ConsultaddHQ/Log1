import json
from datetime import datetime
from django.db.models import Q

from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin

from engineering.serializers import *
from marketing.utils import date_filter
from project.models import Project, ProjectSupport
from activity.serializers import Activity, ActivitySerializer
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from notification.utils import create_notification, push_notification
from project.serializers import ProjectSupportSerializer, ProjectSupportCreateSerializer
from engineering.serializers import TimesheetSerializer, ProjectSupportUpdateSerializer, ProjectDescriptionSerializer


# Route - /engineering/
class EngineeringViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Project.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = EngineeringSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', None)
            filter_for = request.GET.get('filter_for', 'all')
            filter_json = request.GET.get('filter_json', None)
            first, last = get_page_limits(request)

            projects = Project.objects.filter(
                statuses__is_current=True, statuses__status__in=['new', 'received', 'on_boarded', 'joined'],
            )
            filters = {}
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

            counts = {
                "training": {
                    "display_name": "Training",
                    "count": projects.filter(start_date__gt=date.today(), support__statuses__is_current=True,
                                             support__statuses__frequency='more_than_2_days').count()
                },
                "active": {
                    "display_name": "Active",
                    "count": projects.filter(start_date__lte=date.today(), support__statuses__is_current=True,
                                             support__statuses__frequency='more_than_2_days').count()
                },
                "less_active": {
                    "display_name": "Less Active",
                    "count": projects.filter(support__statuses__is_current=True,
                                             support__statuses__frequency='less_than_3_days').count()
                },
                "independent": {
                    "display_name": "Independent",
                    "count": projects.filter(support__statuses__is_current=True,
                                             support__statuses__frequency__in=['independent', 'twice_a_month']).count()
                },
            }

            if filter_json:
                if 'support_status' in filters:
                    if filters['support_status'] == 'training':
                        projects = projects.filter(
                            start_date__gt=date.today(),
                            support__statuses__is_current=True,
                            support__statuses__frequency='more_than_2_days',
                        )
                    elif filters['support_status'] == 'active':
                        projects = projects.filter(
                            start_date__lte=date.today(),
                            support__statuses__is_current=True,
                            support__statuses__frequency='more_than_2_days',
                        )
                    elif filters['support_status'] == 'less_active':
                        projects = projects.filter(
                            support__statuses__is_current=True,
                            support__statuses__frequency='less_than_3_days',
                        )
                    elif filters['support_status'] == 'independent':
                        projects = projects.filter(
                            support__statuses__is_current=True,
                            support__statuses__frequency__in=['independent', 'twice_a_month'],
                        )

            total = projects.count()
            serializer = self.serializer_class(projects[first:last], many=True)
            return Response({"data": serializer.data, "total": total, "counts": counts}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            qs = Project.objects.filter(id=kwargs.get('pk', None))
            if qs:
                serializer = EngineeringDetailSerializer(qs.first())
                return Response({"data": serializer.data}, status=200)
            return Response({"message": "Project not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path="filters")
    def filters(self, request):
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
            return Response({"message": ERROR_MSG, 'error': str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="activity")
    def activity(self, request, pk):
        try:
            activities = Activity.objects.filter(object_id=pk, content_type__model='project_support')
            serializer = ActivitySerializer(activities.order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="timesheet")
    def timesheet(self, request, pk):
        try:
            first, last = get_page_limits(request)
            start = request.GET.get('start', None)
            end = request.GET.get('end', date.today())
            qs = Project.objects.filter(id=pk)
            if qs:
                timesheets = qs.first().timesheets.exclude(status='draft')
                if start:
                    timesheets = timesheets.filter(start__range=[start, end])
                total = timesheets.count()
                serializer = TimesheetSerializer(timesheets[first:last], many=True)
                return Response({"data": serializer.data, 'total': total}, status=200)
            return Response({"message": "Project not found"}, status=404)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/<project_id>/support/
class ProjectSupportViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin):
    queryset = ProjectSupport.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectSupportSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('id'))
            serializer = self.serializer_class(project.support.all().order_by('-created'), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('id'))
            support = get_object_or_404(User, id=request.data.get('support'))
            serializer = ProjectSupportCreateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            consultant = project.submission.consultant
            title = f"""{support.employee_name} assigned as support person to {consultant.name}'s project at
                            {project.submission.client}"""
            notification_data = {
                'category': 'info', 'target_type': 'projectsupport', 'parent_type': 'project',
                'title': title, 'target_id': None, 'description': title, 'parent_id': project.id,
                'sender_id': request.user.id, 'recipient_user_type': 'user', 'sender_user_type': 'user',
            }
            user_list = [project.submission.created_by]
            pocs = consultant.pocs.all()
            for data in pocs:
                user_list.append(data.poc)
            create_notification(user_list, notification_data)

            message_body = {
                "click_action": "https://app.log1.com", "show_in_foreground": True,
                "body": title, "title": title, "category": "alert",
                "data": {
                    'is_read': False, 'sub_target': 'support', 'timestamp': str(datetime.now()),
                    'is_deleted': False, 'target': 'project', 'target_id': project.id,
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            return Response({"data": "Support person added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            project_support_id = kwargs.get('pk')
            project_support = get_object_or_404(ProjectSupport, id=project_support_id)
            serializer = ProjectSupportCreateSerializer(project_support, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Support is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /project/<project_id>/support_status/
class ProjectSupportStatusViewSet(GenericViewSet, CreateModelMixin, UpdateModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = ProjectSupportStatus.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportStatusSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = ProjectSupportStatusSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Support Status is updated"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            status_id = kwargs.get('pk')
            status = get_object_or_404(ProjectSupportStatus, id=status_id)
            serializer = ProjectSupportStatusSerializer(status, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Support Status is updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /project/<project_id>/updates/
class ProjectSupportUpdateViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = ProjectSupportUpdate.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectSupportUpdateSerializer

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('id'))
            serializer = ProjectSupportUpdateSerializer(project.updates.all(), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            serializer = ProjectSupportUpdateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Update is added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectSupportUpdate, id=kwargs.get('pk'))
            serializer = ProjectSupportUpdateSerializer(update, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Update is edited"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)
