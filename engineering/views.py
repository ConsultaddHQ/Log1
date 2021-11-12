import json
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
from activity.views import create_activity
from engineering.utils import tag_and_notify
from attachment.models import Attachment, create_attachment
from activity.serializers import Activity, ActivitySerializer
from log1.utils import ERROR_MSG, get_page_limits, write_exception
from engineering.serializers import TimesheetSerializer, ProjectUpdateSerializer, ProjectDescriptionSerializer


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
                        projects = projects.exclude(support=None)
                    if filters['assignment'] == 'unassigned':
                        projects = projects.filter(support=None)

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
                "support_status": {
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
                        "count": projects.filter(
                            support__statuses__is_current=True,
                            support__statuses__frequency__in=['independent', 'twice_a_month']
                        ).count()
                    },
                },
                "project_status": {
                    "new": {
                        "display_name": "New",
                        "count": projects.filter(statuses__is_current=True, statuses__status='new').count(),
                    },
                    "received": {
                        "display_name": "Received",
                        "count": projects.filter(statuses__is_current=True, statuses__status='received').count(),
                    },
                    "on_boarded": {
                        "display_name": "On Boarded",
                        "count": projects.filter(statuses__is_current=True, statuses__status='on_boarded').count(),
                    },
                    "joined": {
                        "display_name": "Joined",
                        "count": projects.filter(statuses__is_current=True, statuses__status='joined').count(),
                    },
                    "complete": {
                        "display_name": "Complete",
                        "count": projects.filter(statuses__is_current=True, statuses__status='complete').count(),
                    },
                    "cancelled": {
                        "display_name": "Cancelled",
                        "count": projects.filter(
                            statuses__is_current=True,
                            statuses__status__istartswith='cancelled').count(),
                    },
                    "terminated": {
                        "display_name": "Terminated",
                        "count": projects.filter(
                            statuses__is_current=True,
                            statuses__status__istartswith='terminated').count(),
                    }
                }
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
            activities = Activity.objects.filter(
                object_id=pk,
                content_type__model__in=['projectsupport', 'projectupdate', 'projectdescription']
            )
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


# Route - /project/:project_id:/update/
class ProjectUpdateViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin):
    queryset = ProjectUpdate.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectUpdateSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('id'))
            serializer = ProjectUpdateGetSerializer(project.updates.all(), many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectUpdate, id=kwargs.get('pk'))
            serializer = ProjectUpdateGetSerializer(update)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            data['project'] = kwargs.get('id')
            data['update_by'] = request.user.id
            serializer = self.serializer_class(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            update = ProjectUpdate.objects.get(id=serializer.data['id'])
            for file in request.FILES.getlist('files'):
                file_data = {
                    "file": file,
                    "object_id": update.id,
                    "creator": request.user,
                    "model": "projectupdate",
                    "type": 'project_update',
                }
                create_attachment(file_data)
            tags = request.data.get('tagged_user', '')
            tag_and_notify(update, tags, request.user, 'create')

            # Activity
            desc = f"{request.user.employee_name} added project Update-{update.id}"
            create_activity(data['project'], 'projectupdate', request.user, desc, 'created')
            return Response({"message": "Project Update is added successfully"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectUpdate, id=kwargs.get('pk'))
            serializer = self.serializer_class(update, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            tags = request.data.get('tagged_user', '')
            tag_and_notify(update, tags, request.user, 'update')

            # Activity
            desc = f"{request.user.employee_name} edited project Update-{update.id}"
            create_activity(update.project.id, 'projectupdate', request.user, desc, 'update')

            return Response({"message": "Project update is edited successfully"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['put'], detail=True, url_path='add_document')
    def add_document(self, request, project_id, pk):
        try:
            update = get_object_or_404(ProjectUpdate, id=pk)
            file_data = {
                "object_id": update.id,
                "creator": request.user,
                "model": "projectupdate",
                "type": 'project_update',
                "file": request.FILES.get('file'),
            }
            if create_attachment(file_data):
                # Activity
                desc = f"{request.user.employee_name} uploaded {file_data['file']} file"
                create_activity(update.id, 'projectupdate', request.user, desc, 'update')
                return Response({"message": "Document is uploaded"}, status=202)
            return Response({"message": "Error in uploading document"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='remove_document')
    def remove_document(self, request, project_id, pk):
        try:
            update = get_object_or_404(ProjectUpdate, id=pk)
            attachment = get_object_or_404(Attachment, id=request.data.get('attachment_id'))
            if update.update_by.id == request.user.id or attachment.creator.id == request.user.id:
                file_name = attachment.attachment_file.name
                attachment.delete()
                # Activity
                desc = f"{request.user.employee_name} removed {file_name} file"
                create_activity(update.id, 'projectupdate', request.user, desc, 'update')
                return Response({"message": "Document removed"}, status=202)
            return Response({"message": "Error in deleting document"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/:project_id:/description/
class ProjectDescriptionViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = ProjectDescription.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectDescriptionSerializer

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('id'))
            if hasattr(project, 'description'):
                serializer = self.serializer_class(project.description)
                return Response({"data": serializer.data}, status=200)
            return Response({"data": []}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            data['project'] = kwargs.get('id')
            data['update_by'] = request.user.id
            serializer = self.serializer_class(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Activity
            desc = f"{request.user.employee_name} added project description"
            create_activity(serializer.data['id'], 'projectdescription', request.user, desc, 'create')
            return Response({"message": "Description added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            description = get_object_or_404(ProjectDescription, id=kwargs.get('pk'))
            serializer = self.serializer_class(description, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            # Activity
            desc = f"{request.user.employee_name} updated project description"
            create_activity(description.id, 'projectdescription', request.user, desc, 'update')
            return Response({"message": "Description Updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)
