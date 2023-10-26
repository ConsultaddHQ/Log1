import os
import json
import copy
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.db.models import Q, Max

from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from engineering.utils import *
from employee.models import Team, Role
from engineering.serializers import *
from marketing.models import Interview
from marketing.utils import date_filter
from utils_app.utils import TECHNOLOGIES, export_to_csv
from activity.views import create_activity
from employee.serializers import TeamSerializer
from attachment.models import Attachment, create_attachment
from activity.serializers import Activity, ActivitySerializer
from log1.utils import ERROR_MSG, DONT_HAVE_ACCESS, get_page_limits, write_exception


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

            projects = Project.objects.filter(statuses__is_current=True)
            filters = {}
            if filter_json:
                filters = json.loads(filter_json)

                start_date = filters.get('start_date', None)
                projects = date_filter(projects, start_date, 'start_date')

                if 'support' in filters:
                    projects = projects.filter(support__support_id=filters['support'])

                if 'client' in filters:
                    projects = projects.filter(submission__client__iexact=filters['client'])

                if 'teams' in filters:
                    projects = projects.filter(submission__marketing_team__iexact=filters['teams'])

                if 'status' in filters:
                    projects = projects.filter(statuses__status__istartswith=filters['status'], statuses__is_current= True)

                if 'assignment' in filters:
                    if filters['assignment'] == 'assigned':
                        projects = projects.filter(
                            support_required=True, support__isnull=False, created__gt="2021-10-01"
                        )
                    if filters['assignment'] == 'unassigned':
                        projects = projects.filter(
                            support_required=True, support__isnull=True, created__gt="2021-10-01"
                        )
                    if filters['assignment'] == 'old_projects':
                        projects = projects.filter(created__lt="2021-10-01")
                    if filters['assignment'] == 'support_not_required':
                        projects = projects.filter(support_required=False)

            if filter_for == 'my':
                projects = projects.filter(support__support=request.user)

            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(support__support__employee_name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            projects = projects.order_by('-id').distinct('id')

            counts = {
                "support_status": {
                    "training": {
                        "display_name": "Training",
                        "count": projects.filter(
                            support__statuses__frequency='active', support_required=True,
                            start_date__gt=date.today(), support__statuses__is_current=True,
                        ).count()
                    },
                    "active": {
                        "display_name": "Active",
                        "count": projects.filter(
                            support__statuses__frequency='active', support_required=True,
                            start_date__lte=date.today(), support__statuses__is_current=True,
                        ).count()
                    },
                    "less_active": {
                        "display_name": "Less Active",
                        "count": projects.filter(support__statuses__is_current=True, support_required=True,
                                                 support__statuses__frequency='less_active').count()
                    },
                    "independent": {
                        "display_name": "Independent",
                        "count": projects.filter(support__statuses__is_current=True, support_required=True,
                                                 support__statuses__frequency='independent').count()
                    },
                    "handover": {
                        "display_name": "Handover",
                        "count": projects.filter(support__statuses__is_current=True, support_required=True,
                                                 support__statuses__frequency='handover').count()

                    },
                    "terminated": {
                        "display_name": "Terminated",
                        "count": projects.filter(support__statuses__is_current=True, support_required=True,
                                                 support__statuses__frequency='terminated').count()
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
                },
                "assignment_count": {
                    "all": {
                        "display_name": "All",
                        "count": Project.objects.all().count()

                    },
                    "assigned": {
                        "display_name": "Assigned",
                        "count": projects.filter(
                            support_required=True, support__isnull=False, created__gt="2021-10-01"
                        ).count(),
                    },
                    "unassigned": {
                        "display_name": "Unassigned",
                        "count": projects.filter(
                            support_required=True, support__isnull=True, created__gt="2021-10-01"
                        ).count(),
                    },
                    "old_projects": {
                        "display_name": "Old Projects",
                        "count": projects.filter(created__lte="2021-10-01").count(),
                    },
                    "support_not_required": {
                        "display_name": "Support Not Required",
                        "count": projects.filter(support_required=False).count(),
                    }
                }
            }

            if filter_json:
                if 'support_status' in filters:
                    if filters['support_status'] == 'training':
                        projects = projects.filter(
                            support_required=True,
                            start_date__gt=date.today(),
                            support__statuses__is_current=True,
                            support__statuses__frequency='active',
                        )
                    elif filters['support_status'] == 'active':
                        projects = projects.filter(
                            support_required=True,
                            start_date__lte=date.today(),
                            support__statuses__is_current=True,
                            support__statuses__frequency='active',
                        )
                    elif filters['support_status'] == 'less_active':
                        projects = projects.filter(
                            support_required=True,
                            support__statuses__is_current=True,
                            support__statuses__frequency='less_active',
                        )
                    elif filters['support_status'] == 'independent':
                        projects = projects.filter(
                            support_required=True,
                            support__statuses__is_current=True,
                            support__statuses__frequency='independent'
                        )
                    elif filters['support_status'] == 'handover':
                        projects = projects.filter(
                            support_required=True,
                            support__statuses__is_current=True,
                            support__statuses__frequency='handover'
                        )
                    elif filters['support_status'] == 'terminated':
                        projects = projects.filter(
                            support_required=True,
                            support__statuses__is_current=True,
                            support__statuses__frequency='terminated'
                        )

            total = projects.count()
            if filters.get('status', None) not in ['complete', 'cancelled', 'terminated']:
                projects = projects.filter(statuses__status__in=['new', 'received', 'on_boarded', 'joined'])

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
            data = {
                "project_status": [
                    {'name': 'new', 'display_name': 'New'},
                    {'name': 'received', 'display_name': 'Received'},
                    {'name': 'on_boarded', 'display_name': 'On Boarded'},
                    {'name': 'joined', 'display_name': 'Joined'},
                    {'name': 'complete', 'display_name': 'Complete'},
                    {'name': 'cancelled', 'display_name': 'Cancelled'},
                    {'name': 'terminated', 'display_name': 'Terminated'},
                ],
                "support_status": [
                    {'name': 'training', 'display_name': 'Training'},
                    {'name': 'active', 'display_name': 'Active'},
                    {'name': 'less_active', 'display_name': 'Less Active'},
                    {'name': 'independent', 'display_name': 'Independent'},
                    {'name': 'handover', 'display_name': 'Handover'},
                    {'name': 'terminated', 'display_name': 'Terminated'},
                ],
                "assignment_status": [
                    {'name': 'all', 'display_name': 'All'},
                    {'name': 'assigned', 'display_name': 'Assigned'},
                    {'name': 'unassigned', 'display_name': 'Unassigned'},
                    {'name': 'old_projects', 'display_name': 'Old Projects'},
                    {'name': 'support_not_required', 'display_name': 'Support Not Required'},
                ]
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
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path="timesheet")
    def timesheet(self, request, pk):
        try:
            first, last = get_page_limits(request)
            start = request.GET.get('start', None)
            end = request.GET.get('end', date.today().strftime('%Y-%m-%d'))
            projects = Project.objects.filter(id=pk)
            if projects:
                timesheets = projects.first().timesheets.exclude(status='draft')
                if start:
                    if not end:
                        end = date.today().strftime('%Y-%m-%d')
                    timesheets = timesheets.filter(start__range=[start, end])
                total = timesheets.count()
                serializer = TimesheetSerializer(timesheets[first:last], many=True)
                return Response({"data": serializer.data, 'total': total}, status=200)
            return Response({"message": "Project not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='guidelines')
    def guidelines(self, request):
        try:
            file = open('data/first_day_guideline.txt', 'r')
            first_day = file.read()
            file.close()

            file = open('data/project_guidelines.txt', 'r')
            project = file.read()
            file.close()

            data = {
                "first_day": first_day,
                "guideline": project
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='support_required')
    def support(self, request, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            project.support_required = request.data.get('is_required')
            project.save()

            # create_activity
            support_required = "required" if project.support_required is True else "not required"
            desc = f"{request.user.employee_name} marked project support as {support_required}"
            create_activity(project.id, 'projectdescription', request.user, desc, 'update')
            return Response({"message": f"project support marked as {support_required}"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/:project_id:/update/
class ProjectUpdateViewSet(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin):
    queryset = ProjectUpdate.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectUpdateSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
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
            data = copy.copy(request.data)
            data['update_by'] = request.user.id
            data['project'] = kwargs.get('project_id')
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

    @action(methods=['put'], detail=True, url_path='blocker')
    def blocker(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectUpdate, id=kwargs.get('pk'))
            update.blocker_resolved = request.data.get('blocker_resolved', update.blocker_resolved)
            update.blocker_solution = request.data.get('blocker_solution', update.blocker_solution)
            update.save()

            # Activity
            if update.blocker_resolved:
                desc = f"{request.user.employee_name} edited Project Update-{update.id} and marked blocker resolved."
                create_activity(update.id, 'projectupdate', request.user, desc, 'update')
            return Response({"message": "Project update edited successfully"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='add_document')
    def add_document(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectUpdate, id=kwargs.get('pk'))
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
    def remove_document(self, request, *args, **kwargs):
        try:
            update = get_object_or_404(ProjectUpdate, id=kwargs.get('pk'))
            attachment = get_object_or_404(Attachment, id=request.data.get('attachment_id'))
            if update.update_by.id == request.user.id or attachment.creator.id == request.user.id:
                file_name = attachment.attachment_file.name
                attachment.delete()
                # Activity
                desc = f"{request.user.employee_name} removed {file_name} file"
                create_activity(update.project.id, 'projectupdate', request.user, desc, 'update')
                return Response({"message": "Document removed"}, status=202)
            return Response({"message": "Error in deleting document"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/:project_id:/summary/
class ProjectSummaryViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = ProjectDescription.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = ProjectDescriptionSerializer

    def list(self, request, *args, **kwargs):
        try:
            resume, description_data, recording = None, None, list()
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
            interviews = Interview.objects.filter(submission__project__id=kwargs.get('project_id'))
            for interview in interviews:
                if interview.attachment_link:
                    recording.append({
                        "id": interview.id,
                        "name": interview.attachment_link.split('/')[-1]
                    })

            resume_attachment = Attachment.objects.filter(object_id=project.submission.id, attachment_type='resume')
            if resume_attachment:
                resume = {
                    "id": resume_attachment.first().id,
                    "name": os.path.split(resume_attachment.first().attachment_file.name)[1]
                }
            description_qs = ProjectDescription.objects.filter(project=project)
            if description_qs:
                description = description_qs.first()
                description_data = {
                    "id": description.id,
                    "notes": description.notes,
                    "remark": description.remark,
                    "resource": description.resource,
                    "timezone": description.timezone,
                    "technology": description.technology,
                    "description": description.description,
                    "daily_support_hour": description.daily_support_hour,
                    "consultant_preferred_time": description.consultant_preferred_time
                }
            recruiter, retention = project.consultant.recruiter, project.consultant.relation
            data = {
                "resume": resume,
                "recordings": recording,
                "description": description_data,
                "job_description": project.submission.lead.job_desc,
                "recruiter": {
                    "id": recruiter.id,
                    "email": recruiter.email,
                    "name": recruiter.employee_name,
                } if recruiter else None,
                "retention": {
                    "id": retention.id,
                    "email": retention.email,
                    "name": retention.employee_name,
                } if retention else None,
                "marketer": {
                    "id": project.submission.created_by.id,
                    "email": project.submission.created_by.email,
                    "name": project.submission.created_by.employee_name,
                },
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('project_id'))
            if hasattr(project, 'description'):
                serializer = ProjectDescriptionSerializer(project.description, request.data, partial=True)
            else:
                data = request.data.copy()
                data['project'] = project.id
                data['update_by'] = request.user.id
                serializer = ProjectDescriptionSerializer(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Activity
            if 'notes' in request.data:
                desc = f"{request.user.employee_name} updated the interview notes"
            elif 'remark' in request.data:
                desc = f"{request.user.employee_name} updated the project description"
            else:
                desc = f"{request.user.employee_name} updated the project description"
            create_activity(project.id, 'projectdescription', request.user, desc, 'created')

            return Response({"message": "Project description created", "data": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            description = ProjectDescription.objects.get(id=kwargs.get('pk'))
            serializer = ProjectDescriptionSerializer(description, request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Activity
            if 'notes' in request.data:
                desc = f"{request.user.employee_name} updated the interview notes"
            elif 'remark' in request.data:
                desc = f"{request.user.employee_name} updated the project description"
            else:
                desc = f"{request.user.employee_name} updated the project description"
            create_activity(description.project.id, 'projectdescription', request.user, desc, 'update')

            return Response({"message": "Project description updated", "data": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='technology')
    def technology(self, request, *args, **kwargs):
        data = ['Python', 'Java', 'Nodejs', 'JavaScript', 'ReactJS', 'Angular', 'SQL', 'AWS', 'DevOps', 'BA', 'DA',
                'Peoplesoft', 'Workday', 'Kronos', 'Lawson', 'Full Stack', 'Salesforce', 'Cyber Security']
        return Response({"data": data}, status=200)

    @action(methods=['get', 'put'], detail=False, url_path='resource')
    def resource(self, request, project_id):
        try:
            project = get_object_or_404(Project, id=project_id)
            if request.method == 'PUT':
                description, _ = ProjectDescription.objects.get_or_create(project=project)
                description.resource = request.data.get('resource')
                description.save()

                # Activity
                desc = f"{request.user.employee_name} updated project resource"
                create_activity(description.project.id, 'projectdescription', request.user, desc, 'update')

                return Response({"message": "Project description updated"}, status=202)
            else:
                if hasattr(project, 'description'):
                    description = get_object_or_404(ProjectDescription, project=project)
                    return Response({"data": {'id': description.id, "resource": description.resource}}, status=200)
                return Response({"message": "Project Resource not found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get', 'put', 'delete'], detail=False, url_path='document')
    def document(self, request, project_id):
        try:
            project = get_object_or_404(Project, id=project_id)
            if request.method == 'PUT':
                description, _ = ProjectDescription.objects.get_or_create(project=project)
                if request.FILES.get('file', None):
                    content_type = ContentType.objects.get(model='projectdescription')
                    Attachment.objects.create(
                        creator=request.user,
                        object_id=description.id,
                        content_type=content_type,
                        attachment_type='project_resource',
                        attachment_file=request.FILES.get('file'),
                    )
                    return Response({"message": "Resource Uploaded"}, status=201)
                return Response({"message": "File not found"}, status=400)
            elif request.method == 'DELETE':
                attachment_id = request.GET.get('attachment_id')
                attachment = get_object_or_404(Attachment, id=attachment_id, creator=request.user)
                desc = f"{attachment.filename} deleted from resources section by {request.user.employee_name}"
                create_activity(project_id, 'projectdescription', request.user, desc, 'deleted')
                attachment.attachment_file.delete(save=False)
                attachment.delete()
                return Response({"message": "Attachment deleted"}, status=204)
            else:
                description = get_object_or_404(ProjectDescription, project_id=project.id)
                serializer = AttachmentGetSerializer(description.attachments.all(), many=True)
                return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/:project_id:/training/
class TrainingAgendaViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, CreateModelMixin, DestroyModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = TrainingAgenda.objects.all()
    serializer_class = TrainingAgendaSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            agendas = TrainingAgenda.objects.filter(project_id=kwargs.get('project_id'))
            serializer = self.serializer_class(agendas, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            old_position = 0
            qs = TrainingAgenda.objects.filter(project_id=kwargs.get('project_id'))
            if qs:
                old_position = qs.aggregate(Max('position'))['position__max']

            TrainingAgenda.objects.create(
                created_by=request.user,
                position=old_position + 1,
                remark=request.data.get('remark'),
                project_id=kwargs.get('project_id'),
                duration=request.data.get('duration'),
                description=request.data.get('description'),
                assignment_given=request.data.get('assignment_given'),
            )

            # Activity
            desc = f"{request.user.employee_name} added training agenda {old_position + 1}"
            create_activity(kwargs.get('project_id'), 'trainingagenda', request.user, desc, 'created')

            return Response({"message": "Agenda added"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            qs = TrainingAgenda.objects.filter(id=kwargs.get('pk'), created_by=request.user)
            if not qs:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)
            agenda = qs.first()
            serializer = self.serializer_class(agenda, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Activity
            desc = f"{request.user.employee_name} updated training agenda {agenda.position}"
            create_activity(kwargs.get('project_id'), 'trainingagenda', request.user, desc, 'updated')

            return Response({"message": "Agenda updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            qs = TrainingAgenda.objects.filter(id=kwargs.get('pk'), created_by=request.user)
            if not qs:
                return Response({"message": DONT_HAVE_ACCESS}, status=403)

            position = qs.first().position
            qs.delete()

            # Activity
            desc = f"{request.user.employee_name} deleted training agenda {position}"
            create_activity(kwargs.get('project_id'), 'trainingagenda', request.user, desc, 'deleted')

            return Response({"message": "Agenda Deleted"}, status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /project/:project_id:/checklist/
class TrainingCheckListViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = TrainingCheckList.objects.all()
    serializer_class = TrainingCheckListSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            checklist = TrainingCheckList.objects.filter(project_id=kwargs.get('project_id')).order_by('position')
            serializer = self.serializer_class(checklist, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            checklist = get_object_or_404(TrainingCheckList, id=kwargs.get('pk'))
            checklist.status = request.data.get('status')
            checklist.remark = request.data.get('remark', None)
            checklist.save()

            # Activity
            desc = f"{request.user.employee_name} updated checklist {checklist.position}"
            create_activity(kwargs.get('project_id'), 'trainingchecklist', request.user, desc, 'updated')
            return Response({"message": "Checklist updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /engineer_report/
class EngineerReportViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = EngineerReportSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def support_status_filter(queryset, support_status):
        if support_status == 'training':
            queryset = queryset.filter(
                statuses__is_current=True,
                statuses__frequency='active',
                project__start_date__gte=date.today()
            )
        elif support_status == 'active':
            queryset = queryset.filter(
                statuses__is_current=True,
                statuses__frequency='active',
                project__start_date__lte=date.today()
            )
        elif support_status == 'less_active':
            queryset = queryset.filter(
                statuses__is_current=True,
                statuses__frequency='less_active'
            )
        elif support_status == 'independent':
            queryset = queryset.filter(
                statuses__is_current=True,
                statuses__frequency='independent'
            )
        return queryset

    @staticmethod
    def project_filter_counts(queryset):
        return {
            "support_status": {
                "active": {
                    "display_name": "Active",
                    "count": queryset.filter(
                        end=None, project__start_date__lte=date.today(),
                        statuses__is_current=True, statuses__frequency='active',
                    ).count()},
                "training": {
                    "display_name": "Training",
                    "count": queryset.filter(
                        statuses__is_current=True, end=None,
                        statuses__frequency='active', project__start_date__gt=date.today(),
                    ).count()
                },
                "less_active": {
                    "display_name": "Less Active",
                    "count": queryset.filter(
                        statuses__frequency='less_active', end=None, statuses__is_current=True,
                    ).count()
                },
                "independent": {
                    "display_name": "Independent",
                    "count": queryset.filter(
                        statuses__frequency='independent', end=None, statuses__is_current=True,
                    ).count()
                },
                "handover": {
                    "display_name": "Handover",
                    "count": queryset.filter(
                        statuses__frequency='independent', end=None, statuses__is_current=True,
                    ).count()
                },
                "terminated": {
                    "display_name": "Terminated",
                    "count": queryset.filter(
                        statuses__frequency='independent', end=None, statuses__is_current=True,
                    ).count()
                },
                "total": {
                    "display_name": "Total",
                    "count": queryset.filter(statuses__is_current=True, end=None).count()
                },
            },
        }

    @staticmethod
    def interview_status_filter_count(queryset):
        return [
            {"name": "Offer", "count": queryset.filter(status='offer').count()},
            {"name": "Failed", "count": queryset.filter(status='failed').count()},
            {"name": "Cancelled", "count": queryset.filter(status='cancelled').count()},
            {"name": "Next Round", "count": queryset.filter(status='next_round').count()},
            {"name": "Feedback Due", "count": queryset.filter(status='feedback_due').count()},
        ]

    @staticmethod
    def test_status_filter_count(queryset):
        return [
            {"name": "New", "count": queryset.filter(status='new').count()},
            {"name": "Passed", "count": queryset.filter(status='passed').count()},
            {"name": "Failed", "count": queryset.filter(status='failed').count()},
            {"name": "Assigned", "count": queryset.filter(status='assigned').count()},
            {"name": "Cancelled", "count": queryset.filter(status='cancelled').count()},
            {"name": "Feedback_due", "count": queryset.filter(status='feedback_due').count()},
        ]

    @staticmethod
    def filter_by_time(duration):
        last = date.today().replace(day=1) - timedelta(days=1)

        if duration == 'last_month':
            first = last.replace(day=1)

        elif duration == 'this_quarter':
            last = date.today()
            if last.month < 6:
                first = last + timedelta(days=1) + relativedelta(months=-last.month + 1)
            else:
                first = last + timedelta(days=1) + relativedelta(months=-last.month + 6)
            first = first.replace(day=1)
            last = last + timedelta(days=1)

        elif duration == 'last_quarter':
            if last.month < 6:
                last = last + timedelta(days=1) + relativedelta(months=-last.month)
                first = last + timedelta(days=1) + relativedelta(months=-6)
            else:
                last = last + timedelta(days=1) + relativedelta(months=-last.month + 6)
                first = last + timedelta(days=1) + relativedelta(months=-6)

        elif duration == 'last_6_month':
            last = date.today() + timedelta(days=1)
            first = last + timedelta(days=1) + relativedelta(months=-6)

        elif duration == 'last_12_month':
            last = date.today() + timedelta(days=1)
            first = last + timedelta(days=1) + relativedelta(months=-12)

        # This Month
        else:
            first = date.today().replace(day=1)
            last = date.today() + timedelta(days=1)
        return first, last

    @staticmethod
    def filter_project_status(queryset, project_status):
        if project_status == 'active':
            queryset = queryset.filter(statuses__is_current=True, statuses__status__in=[
                'new', 'joined', 'on_boarded', 'received', 'joined'
            ])
        elif project_status == 'complete':
            queryset = queryset.filter(statuses__is_current=True, statuses__status='complete')
        elif project_status == 'terminated':
            queryset = queryset.filter(statuses__is_current=True, statuses__status__istartswith='terminated')
        return queryset

    @staticmethod
    def project_search(queryset, query, category):
        if query:
            query = query.lstrip().replace(':amp:', '&')
            if category:
                if category == 'consultant_name':
                    queryset = queryset.filter(project__consultant__name__istartswith=query)
                elif category == 'client':
                    queryset = queryset.filter(project__submission__client__istartswith=query)
                elif category == 'vendor_name':
                    queryset = queryset.filter(project__submission__lead__vendor_company__name__istartswith=query)
                else:
                    queryset = queryset.filter(
                        Q(project__consultant__name__istartswith=query) |
                        Q(project__submission__client__istartswith=query) |
                        Q(project__submission__lead__vendor_company__name__istartswith=query)
                    )
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            export = json.loads(request.GET.get('export', 'false'))
            consultant_type = json.loads(request.GET.get('remote', 'false'))
            frequency = json.loads(request.GET.get('status')) \
                if request.GET.get('status', None) else ['active', 'less_active']

            engineers = User.objects.filter(
                projects__statuses__frequency__in=frequency if frequency[0] != 'training' else ['active'],
                is_active=True, projects__end=None, projects__statuses__is_current=True,
                projects__is_proxy_support=False
            ).exclude(role__name__iexact='usa_employee').order_by('employee_id').distinct('employee_id')
            if query:
                query = query.lstrip().replace(':amp:', '&')
                if category:
                    if category == 'support_name':
                        engineers = engineers.filter(employee_name__istartswith=query)
                    elif category == 'consultant_name':
                        engineers = engineers.filter(projects__project__consultant__name__istartswith=query)
                    elif category == 'client':
                        engineers = engineers.filter(projects__project__submission__client__istartswith=query)
                    elif category == 'vendor_name':
                        engineers = engineers.filter(
                            projects__project__submission__lead__vendor_company__name__istartswith=query
                        )
                    else:
                        engineers = engineers.filter(
                            Q(employee_name__istartswith=query) |
                            Q(projects__project__consultant__name__istartswith=query) |
                            Q(projects__project__submission__client__istartswith=query) |
                            Q(projects__project__submission__lead__vendor_company__name__istartswith=query)
                        )

            support = ProjectSupport.objects.filter(support__is_active=True)\
                .exclude((Q(project__statuses__status__istartswith='terminated')
                          | Q(project__statuses__status__istartswith='cancelled') | Q(project__statuses__status='complete')),
                         project__statuses__is_current=True).order_by('project_id').distinct('project_id')
            # if consultant_type:
            #     support = support.filter(project__is_remote=True)
            counts = self.project_filter_counts(support)
            counts['support_status']['total']['count'] = counts['support_status']['active']['count'] + \
                                                         counts['support_status']['less_active']['count'] + \
                                                         counts['support_status']['training']['count']

            support_list = []
            if engineers:
                context = {"frequency": frequency, "type": consultant_type}
                serializer = EngineerReportSerializer(engineers, many=True, context=context)
                if frequency == ['active', 'less_active']:
                    support_list = serializer.data
                else:
                    if serializer.data:
                        for data in serializer.data:
                            if data['project']['bandwidth'] != 0:
                                support_list.append(data)

            # export
            report_url = ""
            if export and support_list:
                report_url = get_engineer_detail_csv(support_list, request)
            return Response({"data": support_list[first: last], "counts": counts, "url": report_url,
                             "total": len(support_list)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='remote_project')
    def remote_project(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            export = json.loads(request.GET.get('export', 'false'))
            project_status = json.loads(request.GET.get('project_status', '[]'))

            projects = Project.objects.filter(is_remote=True)
            if query:
                query = query.lstrip().replace(':amp:', '&')
                if category:
                    if category == 'support_name':
                        projects = projects.filter(support__support__employee_name__istartswith=query)
                    elif category == 'remote_consultant':
                        projects = projects.filter(consultant__name__istartswith=query)
                    elif category == 'client':
                        projects = projects.filter(submission__client__istartswith=query)
                    elif category == 'remote_employee':
                        projects = projects.filter(consultant__name__istartswith=query)
                    elif category == 'consultant_name':
                        projects = projects.filter(
                            submission__consultant_marketing__consultant__name__istartswith=query
                        )
                    else:
                        projects = projects.filter(
                            Q(consultant__name__istartswith=query) |
                            Q(submission__client__istartswith=query) |
                            Q(support__support__employee_name__istartswith=query) |
                            Q(submission__lead__vendor_company__name__istartswith=query) |
                            Q(submission__consultant_marketing__consultant__name__istartswith=query)
                        )

            project_status_counts = {
                "project_status": {
                    "active": {
                        "display_name": "Active",
                        "count": projects.filter(
                            statuses__is_current=True, statuses__status__in=['joined', 'extended']
                        ).count(),
                    },
                    "training": {
                        "display_name": "Training",
                        "count": projects.filter(
                            statuses__is_current=True, statuses__status__in=['new', 'received', 'on_boarded']
                        ).count(),
                    },
                    "closed": {
                        "display_name": "Closed",
                        "count": projects.filter((
                                Q(statuses__status__istartswith='terminated') |
                                Q(statuses__status__istartswith='cancelled') | Q(statuses__status='complete')
                        ), statuses__is_current=True).count(),
                    },
                    "total": {
                        "display_name": "Total",
                        "count": projects.filter(statuses__is_current=True).count(),
                    }
                },
            }
            projects = projects.distinct('id').order_by('id', 'statuses__status')
            if project_status:
                if project_status == ['terminated']:
                    projects = projects.filter(statuses__is_current=True, statuses__status__istartswith='terminated')
                else:
                    projects = projects.filter(statuses__is_current=True, statuses__status__in=project_status)

            else:
                projects = projects.filter(
                    statuses__is_current=True,
                    statuses__status__in=['joined', 'new', 'on_boarded', 'received', 'extended']
                )

            # if support_status:
            #     projects = projects.filter(support__statuses__is_current=True)
            #     if support_status == ['training']:
            #         projects = projects.filter(
            #             support__statuses__frequency=support_status[0], start_date__gt=date.today(),
            #             support__statuses__is_current=True
            #         )
            #     elif support_status == ['active'] or support_status == ['less_active']:
            #         projects = projects.filter(
            #             support__statuses__frequency=support_status[0], support__end=None,
            #             support__statuses__is_current=True
            #         )
            #     else:
            #         projects = projects.filter(
            #             support__statuses__frequency=support_status[0], support__statuses__is_current=True
            #         )

            #     for obj in projects:
            #         if not obj.support.filter(support__employee_name=obj.consultant.name):
            #             final_list.append(obj)
            #
            # if final_list:
            #     projects = final_list
            serializer = RemoteProjectSerializer(projects, many=True)

            # export
            report_url = ""
            if export and serializer.data:
                report_url = get_remote_project_csv(serializer.data, request)

            return Response({"url": report_url, "counts": project_status_counts, "data": serializer.data[first: last],
                             "total": len(serializer.data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='project')
    def project(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            support_status = request.GET.get('status', None)

            projects = ProjectSupport.objects.filter(
                support__id=kwargs.get('pk')
            ).exclude(project__statuses__status__istartswith='terminated', project__statuses__is_current=True)

            projects = self.project_search(projects, query, category)

            total_count = projects.count()
            if support_status:
                projects = self.support_status_filter(projects, support_status)

            serializer = EngineerProjectSerializer(projects[first: last], many=True)
            return Response({"data": serializer.data, "count": total_count}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='test')
    def test(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            start = request.GET.get('start', None)
            end = request.GET.get('end', None)
            test_status = request.GET.get('status', None)
            test = Test.objects.filter(engineer=kwargs.get('pk'))
            
            if test_status:
                test = test.filter(status=test_status)
            if start and end:
                test = test.filter(created__range=[start, end])
            if query:
                query = query.lstrip().replace(':amp:', '&')
                if category:
                    if category == 'consultant_name':
                        test = test.filter(submission__consultant_marketing__consultant__name__istartswith=query)
                    elif category == 'client':
                        test = test.filter(submission__client__istartswith=query)
                    elif category == 'vendor_name':
                        test = test.filter(submission__lead__vendor_company__name__istartswith=query)
                    else:
                        test = test.filter(
                            Q(submission__client__istartswith=query) |
                            Q(submission__lead__vendor_company__name__istartswith=query) |
                            Q(submission__consultant_marketing__consultant__name__istartswith=query)
                        )

            serializer = EngineerTestSerializer(test[first: last], many=True)
            return Response({"data": serializer.data, "count": test.count()}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='interview')
    def interview(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            guest_type = request.GET.get('type', 'all')

            if guest_type == 'guest':
                interview = Interview.objects.filter(guest=kwargs.get('pk'))
            elif guest_type == 'ctb':
                interview = Interview.objects.filter(supervisor=kwargs.get('pk'))
            else:
                interview = Interview.objects.filter(Q(guest=kwargs.get('pk')) | Q(supervisor=kwargs.get('pk')))

            if query:
                query = query.lstrip().replace(':amp:', '&')
                if category:
                    query = query.lstrip().replace(':amp:', '&')
                    if category == 'consultant_name':
                        interview = interview.filter(
                            submission__consultant_marketing__consultant__name__istartswith=query
                        )
                    elif category == 'client':
                        interview = interview.filter(submission__client__istartswith=query)
                    elif category == 'vendor_name':
                        interview = interview.filter(submission__lead__vendor_company__name__istartswith=query)
                    else:
                        interview = interview.filter(
                            Q(submission__client__istartswith=query) |
                            Q(submission__lead__vendor_company__name__istartswith=query) |
                            Q(submission__consultant_marketing__consultant__name__istartswith=query)
                        )

            serializer = EngineerInterviewSerializer(interview[first: last], many=True)
            return Response({"data": serializer.data, "count": interview.count()}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='terminated')
    def terminated(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            category = request.GET.get('category', None)
            support_status = request.GET.get('status', None)

            projects = ProjectSupport.objects.filter(
                support__id=kwargs.get('pk'),
                project__statuses__is_current=True,
                project__statuses__status__istartswith='terminated'
            )

            projects = self.project_search(projects, query, category)

            total_count = projects.count()
            if support_status:
                projects = self.support_status_filter(projects, support_status)

            serializer = EngineerProjectSerializer(projects[first: last], many=True)
            return Response({"data": serializer.data, "count": total_count}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='category')
    def category(self, request):
        data = [
            {'name': 'client', 'display_name': 'Client Name'},
            {'name': 'vendor_name', 'display_name': 'Vendor Name'},
            {'name': 'support_name', 'display_name': 'Support Name'},
            {'name': 'consultant_name', 'display_name': 'Consultant Name'},
        ]
        return Response({"data": data}, status=200)

    @action(methods=['get'], detail=True, url_path='summary')
    def summary(self, request, **kwargs):
        try:
            duration = request.GET.get('filter_by', 'this_month')
            start = request.GET.get('start', None)
            end = request.GET.get('end', None)
            if duration == 'custom' and start and end:
                first = start
                last = end
            else:
                first, last = self.filter_by_time(duration)

            projects = ProjectSupport.objects.filter(
                support__id=kwargs.get('pk'), statuses__created__range=[first, last]
            ).distinct()
            project_qs = projects.exclude(project__statuses__status__istartswith='terminated')
            active = self.support_status_filter(project_qs, 'active').count()
            less_active = self.support_status_filter(project_qs, 'less_active').count()
            independent = self.support_status_filter(project_qs, 'independent').count()
            terminated = projects.filter(project__statuses__status__istartswith='terminated').count()
            counts = [
                {"name": "Active", "count": active},
                {"name": "Terminated", "count": terminated},
                {"name": "Less Active", "count": less_active},
                {"name": "Independent", "count": independent},
            ]
            project_counts = {
                "total": projects.count(),
                "status_counts": counts
            }

            queryset = Test.objects.filter(engineer=kwargs.get('pk'), created__range=[first, last])
            test_counts = {
                "total": queryset.count(),
                "status_counts": self.test_status_filter_count(queryset)
            }

            sup_interview_qs = Interview.objects.filter(supervisor_id=kwargs.get('pk'), created__range=[first, last])
            supervisor_interview_counts = self.interview_status_filter_count(sup_interview_qs)
            supervisor_interview = {
                "total": sup_interview_qs.count(),
                "status_counts": supervisor_interview_counts
            }

            guest_qs = Interview.objects.filter(guest=kwargs.get('pk'), created__range=[first, last])
            guest_interview_counts = self.interview_status_filter_count(guest_qs)
            guest_interview = {
                "total": guest_qs.count(),
                "status_counts": guest_interview_counts
            }

            technology_ls, technology = [], []
            for obj in projects:
                if hasattr(obj.project, 'description') and hasattr(obj.project.description, 'technology'):
                    technology_ls.append(obj.project.description.technology)
            [technology_ls.remove(ele) for ele in technology_ls if ele is None]
            distinct_technology_ls = set(technology_ls)
            for item in distinct_technology_ls:
                technology.append({"name": item, "count": technology_ls.count(item)})
            technology_counts = {
                "total": len(technology_ls),
                "status_counts": technology
            }
            engineer_point = EngineerPoint.objects.filter(engineer=kwargs.get('pk'), is_active=True).first()
            data = {
                "test": test_counts,
                "project": project_counts,
                "technology": technology_counts,
                "guest_interview": guest_interview,
                "supervisor_interview": supervisor_interview,
                "points":engineer_point.points if engineer_point else 0.0,
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @staticmethod
    def get_shift(data, request):
        try:
            shifts = User.SHIFT_CHOICE
            for shift in shifts:
                if data == shifts[0]:
                    return shift[1]
            return None
        except Exception as error:
            write_exception(error, request)


# Route - /team_structure/
class EngineeringTeamViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin):
    queryset = Team.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamStructureSerializer
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def filter_engineer(queryset, filters, request):
        try:
            shifts = User.SHIFT_CHOICE
            eng_teams = Team.objects.filter(dept='Engineering')
            inter_section = request.GET.get('inter_section', None)

            if filters:
                if "skills" in filters:
                    if inter_section == "true":
                        queryset = queryset.filter(technology__contains=filters["skills"])
                    else:
                        queryset = queryset.filter(technology__overlap=filters['skills'])
                if "shifts" in filters:
                    queryset = queryset.filter(shift__in=filters['shifts'])
                if "teams" in filters:
                    queryset = queryset.filter(team__id__in=filters['teams'])
            counts = {
                "shift": [
                    {
                        "name": shift[0],
                        "display_name": shift[1],
                        "count": queryset.filter(shift=shift[0]).exclude(shift=None).count()
                    }
                    for shift in shifts
                ],
                "team": [
                    {
                        "display_name": team.name,
                        "count": queryset.filter(team=team).exclude(team=None).count()
                    }
                    for team in eng_teams
                ],
                "skill": [
                    {
                        "display_name": technology,
                        "count": queryset.filter(technology__overlap=[technology]).count()
                    }
                    for technology in TECHNOLOGIES
                ]
            }
            return queryset, counts
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def list(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            filters = json.loads(request.GET.get('filter_json', '{}'))
            engineers = User.objects.filter(team__dept='Engineering', is_active=True)
            if query:
                engineers = engineers.filter(employee_name__istartswith=query)
            engineers, counts = self.filter_engineer(engineers, filters, request)
            serializer = TeamStructureSerializer(engineers[first: last], many=True)
            return Response({"data": serializer.data, "count": counts, "total": len(engineers)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            data = {
                "count": team.employees.filter(is_active=True).count(),
                "id": team.id, "name": team.name, "scrum_timing": team.scrum_timing,
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            if 'superadmin' not in request.user.roles and 'scrum_master' not in request.user.roles:
                return Response({"message": "You don't have access"}, status=400)

            data = request.data
            team = Team.objects.filter(name=data['name'])
            if team:
                return Response({"message": "Team name already in use"}, status=400)
            Team.objects.create(name=data['name'], scrum_timing=data['scrum_timing'],
                                dept='Engineering', email='engineering@consultadd.com')
            return Response({"message": "Team added to log1"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            serializer = TeamSerializer(team, data=request.data, partial=True)
            serializer.is_valid()
            serializer.save()

            # Activity
            desc = f"{request.user.employee_name} update {team.name} details."
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response({"message": "Team Details Updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='export')
    def export(self, request, **kwargs):
        try:
            query = request.GET.get('query', None)
            filters = json.loads(request.GET.get('filter_json', '{}'))
            engineers = User.objects.filter(role__name='engineer', is_active=True)
            if query:
                engineers = engineers.filter(employee_name__istartswith=query)
            engineers, counts = self.filter_engineer(engineers, filters, request)
            serializer = TeamStructureSerializer(engineers, many=True)
            if serializer.data:
                file_url = get_team_structure_xlsx(serializer.data, counts, request)
                return Response({"data": file_url}, status=200)
            return Response({"message": "No Data to export"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=False, url_path='update_shift')
    def shift(self, request, **kwargs):
        try:
            shift = request.data.get('shift', None)
            employee_ids = request.data.get('employee_ids', [])
            if not employee_ids or not shift:
                return Response({"message": "Data not provided"}, status=400)
            for emp_id in employee_ids:
                employee = get_object_or_404(User, id=emp_id)
                employee.shift = shift
                employee.save()
            return Response({"message": "Shift Detail Updated"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='teams')
    def teams(self, request, **kwargs):
        try:
            team_data = []
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            teams = Team.objects.filter(dept='Engineering').order_by('-id')
            if query:
                teams = teams.filter(name__istartswith=query.lstrip().replace(':amp:', '&'))
            for team in teams[first: last]:
                data = {
                    "count": team.employees.filter(is_active=True).count(),
                    "id": team.id, "name": team.name, "scrum_timing": team.scrum_timing,
                    "scrum_master": team.employees.filter(role__name='scrum_master', is_active=True).values(
                        'id', 'employee_name')
                }
                team_data.append(data)

            return Response({"data": team_data, "total": len(teams)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=True, url_path='move_employee')
    def move_employee(self, request, **kwargs):
        try:
            team = get_object_or_404(Team, id=kwargs.get('pk'))
            employee_ids = request.data.get('employee_ids', [])
            if not employee_ids or not team:
                return Response({"message": "Data not provided"}, status=400)

            scrum_masters, employee_added = [], []
            for emp_id in employee_ids:
                employee = get_object_or_404(User, id=emp_id)
                if employee.role.filter(name='scrum_master'):
                    scrum_masters.append(employee.employee_name)
                    continue
                employee_added.append(employee.employee_name)
                employee.team = team
                employee.save()

            # Activity
            employees = ", ".join(emp for emp in employee_added)
            desc = f"{request.user.employee_name} added {employees} to {team.name}"
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response({"message": "Engineers moved successfully", "not_moved": scrum_masters}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['put'], detail=True, url_path='update_scrum')
    def update_scrum(self, request, **kwargs):
        try:
            team_id = kwargs.get('pk')
            employee_id = request.data.get('employee_id', None)
            if not employee_id:
                return Response({"message": "No employee selected"}, status=200)
            scrum_role = Role.objects.get(name='scrum_master')
            employee = get_object_or_404(User, id=employee_id, team_id=kwargs.get('pk'))
            prev_scrum = User.objects.filter(team_id=team_id, role=scrum_role)
            if prev_scrum:
                prev_scrum.first().role.remove(scrum_role)
            employee.role.add(scrum_role)

            # Activity
            desc = f"{request.user.employee_name} made {employee.employee_name} as scrum master for {employee.team.name}"
            create_activity(kwargs.get('pk'), 'team', request.user, desc, 'updated')

            return Response({"message": f"{employee.employee_name} appointed as scrum master for {employee.team.name}"},
                            status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['delete'], detail=True, url_path='remove_team')
    def remove(self, request, pk):
        try:
            team = get_object_or_404(Team, id=pk)
            team_employees = User.objects.filter(team=team)
            team_name = team.name
            if team_employees:
                return Response({"message": f"Some employees still associated to {team_name}"}, status=400)
            team.delete()

            # Activity
            desc = f"{request.user.employee_name} removed team {team_name}"
            create_activity(pk, 'team', request.user, desc, 'deleted')
            return Response({"message": "Team Removed Successfully"}, status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=False, url_path='compare_teams')
    def compare_team(self, request):
        try:
            team_data = []
            team_ids = request.GET.get("team_ids", '')
            if team_ids:
                team_ids = team_ids.split(',')
            teams = Team.objects.filter(dept='Engineering', id__in=team_ids).order_by('-id')
            for team in teams:
                data = {
                    "id": team.id, "team_name": team.name,
                    "employee": team.employees.filter(is_active=True).exclude(role__name='scrum_master').values('id', 'employee_name'),
                    "scrum": team.employees.filter(
                        is_active=True, role__name='admin').values('id', 'employee_name')
                }
                team_data.append(data)

            return Response({"data": team_data, "total": len(teams)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)
