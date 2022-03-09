import os
import json

from django.db.models import Q, Max
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from engineering.serializers import *
from marketing.models import Interview
from marketing.utils import date_filter
from activity.views import create_activity
from engineering.utils import tag_and_notify
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

            projects = Project.objects.filter(
                statuses__is_current=True, statuses__status__in=['new', 'received', 'on_boarded', 'joined'],
            )
            filters = {}
            if filter_json:
                filters = json.loads(filter_json)

                start_date = filters.get('start_date', None)
                projects = date_filter(projects, start_date, 'start_date')

                if 'support' in filters:
                    projects = projects.filter(support__support_id=filters['support'])

                if 'client' in filters:
                    projects = projects.filter(submission__client__iexact=filters['client'])

                if 'status' in filters:
                    projects = projects.filter(statuses__status=filters['status'], statuses__is_current=True)

                if 'assignment' in filters:
                    if filters['assignment'] == 'assigned':
                        projects = projects.filter(support__isnull=False, created__gt="2021-10-01")
                    if filters['assignment'] == 'unassigned':
                        projects = projects.filter(support__isnull=True, created__gt="2021-10-01")

            if filter_for == 'my':
                projects = projects.filter(support__support=request.user)

            if query:
                query = query.lstrip().replace(':amp:', '&')
                projects = projects.filter(
                    Q(submission__client__istartswith=query) |
                    Q(support__support__employee_name__istartswith=query) |
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__lead__vendor_company__name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query)
                )

            projects = projects.order_by('id').distinct('id')

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
                },
                "assignment_count": {
                    "all": {
                        "display_name": "All",
                        "count": Project.objects.filter(
                            statuses__is_current=True, statuses__status__in=['new', 'received', 'on_boarded', 'joined'],
                        ).count(),
                    },
                    "assigned": {
                        "display_name": "Assigned",
                        "count": projects.filter(support__isnull=False, created__gt="2021-10-01").count(),
                    },
                    "unassigned": {
                        "display_name": "Unassigned",
                        "count": projects.filter(support__isnull=True, created__gt="2021-10-01").count(),
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
                ],
                "assignment_status": [
                    {'name': 'all', 'display_name': 'All'},
                    {'name': 'assigned', 'display_name': 'Assigned'},
                    {'name': 'unassigned', 'display_name': 'Unassigned'},
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
            data = request.data.copy()
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
                    "technology": description.technology,
                    "description": description.description,
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
        queryset = queryset.filter(statuses__is_current=True)
        if support_status == 'training':
            queryset = queryset.filter(
                statuses__frequency='more_than_2_days',
                project__start_date__gte=date.today()
            )
        elif support_status == 'active':
            queryset = queryset.filter(
                statuses__frequency='more_than_2_days',
                project__start_date__lte=date.today()
            )
        elif support_status == 'less_active':
            queryset = queryset.filter(
                statuses__frequency='less_than_3_days'
            )
        elif support_status == 'independent':
            queryset = queryset.filter(
                statuses__frequency__in=['independent', 'twice_a_month']
            )
        return queryset

    @staticmethod
    def project_support_filter(queryset, support_status):
        queryset = queryset.filter(projects__statuses__is_current=True)
        if support_status == 'training':
            queryset = queryset.filter(
                support__statuses__frequency='more_than_2_days',
                start_date__gte=date.today()
            )
        elif support_status == 'active':
            queryset = queryset.filter(
                support__statuses__frequency='more_than_2_days',
                start_date__lte=date.today()
            )
        elif support_status == 'less_active':
            queryset = queryset.filter(
                support__statuses__frequency='less_than_3_days'
            )
        elif support_status == 'independent':
            queryset = queryset.filter(
                support__statuses__frequency__in=['independent', 'twice_a_month']
            )
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)

            engineer = User.objects.filter(
                projects__statuses__is_current=True,
                projects__statuses__frequency__in=['more_than_2_days', 'less_than_3_days']
            ).order_by('employee_id').distinct('employee_id')

            if query:
                engineer = engineer.filter(employee_name__istartswith=query.lstrip())

            projects = Project.objects.exclude(statuses__status__istartswith='terminated')

            counts = {
                "support_status": {
                    "active": {
                        "display_name": "Active",
                        "count": self.project_support_filter(projects, 'active').count()
                    },
                    "training": {
                        "display_name": "Training",
                        "count": self.project_support_filter(projects, 'training').count()
                    },
                    "less_active": {
                        "display_name": "Less Active",
                        "count": self.project_support_filter(projects, 'less_active').count()
                    },
                    "independent": {
                        "display_name": "Independent",
                        "count": self.project_support_filter(projects, 'independent').count()
                    },
                },
            }

            serializer = EngineerReportSerializer(engineer[first: last], many=True)
            return Response({"data": serializer.data, "counts": counts, "total": engineer.count()}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='project')
    def project(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            support_status = request.GET.get('status', None)

            projects = ProjectSupport.objects.filter(
                support__id=kwargs.get('pk')
            ).exclude(project__statuses__status__istartswith='terminated', project__statuses__is_current=True)
            if query:
                projects = projects.filter(project__consultant__name__istartswith=query.lstrip())
            if support_status:
                projects = self.support_status_filter(projects, support_status)

            serial = EngineerProjectSerializer(projects[first: last], many=True)
            return Response({"data": serial.data, "count": len(serial.data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='test')
    def test(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            test = Test.objects.filter(engineer=kwargs.get('pk'))
            if query:
                test = test.filter(
                    Q(submission__created_by__employee_name__istartswith=query) |
                    Q(submission__consultant_marketing__consultant__name__istartswith=query),
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
            guest_type = request.GET.get('type', 'all')

            if guest_type == 'guest':
                interview = Interview.objects.filter(guest=kwargs.get('pk'))
            elif guest_type == 'ctb':
                interview = Interview.objects.filter(supervisor=kwargs.get('pk'))
            else:
                interview = Interview.objects.filter(Q(guest=kwargs.get('pk')) | Q(supervisor=kwargs.get('pk')))

            if query:
                interview = interview.filter(submission__consultant_marketing__consultant=query)

            serial = EngineerInterviewSerializer(interview[first: last], many=True)
            return Response({"data": serial.data, "count": len(serial.data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='terminated')
    def terminated(self, request, **kwargs):
        try:
            first, last = get_page_limits(request)
            query = request.GET.get('query', None)
            support_status = request.GET.get('status', None)

            projects = ProjectSupport.objects.filter(
                support__id=kwargs.get('pk'),
                project__statuses__is_current=True,
                project__statuses__status__istartswith='terminated'
            )
            if query:
                projects = projects.filter(project__consultant__name__istartswith=query)
            if support_status:
                projects = self.support_status_filter(projects, support_status)

            serial = EngineerProjectSerializer(projects[first: last], many=True)
            return Response({"data": serial.data, "count": len(serial.data)}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)

    @action(methods=['get'], detail=True, url_path='dashboard')
    def dashboard(self, request, **kwargs):
        try:
            project_qs = ProjectSupport.objects.filter(support__id=kwargs.get('pk'))
            active = project_qs.filter(
                project__start_date__lte=date.today(),
                statuses__is_current=True, statuses__frequency='more_than_2_days',
            ).exclude(project__statuses__status__istartswith='terminated').count()
            less_active = project_qs.filter(
                statuses__frequency='less_than_3_days', statuses__is_current=True
            ).exclude(project__statuses__status__istartswith='terminated').count()
            independent = project_qs.filter(
                statuses__is_current=True, statuses__frequency__in=['independent', 'twice_a_month'],
            ).exclude(project__statuses__status__istartswith='terminated').count()
            terminated = project_qs.filter(project__statuses__status__istartswith='terminated').count()

            total_project = project_qs.count()
            project = {
                "active": 0,
                "terminated": 0,
                "less_active": 0,
                "independent": 0,
                "count": {
                    "active": active,
                    "total": total_project,
                    "terminated": terminated,
                    "less_active": less_active,
                    "independent": independent,
                }
            }
            if total_project != 0:
                project["active"] = int((active/total_project) * 100)
                project["terminated"] = int((terminated/total_project) * 100)
                project["less_active"] = int((less_active/total_project) * 100)
                project["independent"] = int((independent/total_project) * 100)

            test_qs = Test.objects.filter(engineer=kwargs.get('pk'))
            passed = test_qs.filter(status='passed').count()
            failed = test_qs.filter(status='failed').count()
            feedback_due = test_qs.filter(status='feedback_due').count()

            total_test = test_qs.count()
            test = {
                "passed": 0,
                "failed": 0,
                "feedback_due": 0,
                "count": {
                    "passed": passed,
                    "failed": failed,
                    "total": total_test,
                    "feedback_due": feedback_due,
                }
            }
            if total_test != 0:
                test["passed"] = int((passed/total_test) * 100)
                test["failed"] = int((failed/total_test) * 100)
                test["feedback_due"] = int((feedback_due/total_test) * 100)

            sup_interview_qs = Interview.objects.filter(supervisor_id=kwargs.get('pk'))
            sup_offer = sup_interview_qs.filter(status='offer').count()
            sup_failed = sup_interview_qs.filter(status='failed').count()
            sup_next_round = sup_interview_qs.filter(status='next_round').count()
            sup_feedback_due = sup_interview_qs.filter(status='feedback_due').count()

            total_sup_interview = sup_interview_qs.count()
            sup_interview = {
                "offer": 0,
                "failed": 0,
                "next_round": 0,
                "feedback_due": 0,
                "count": {
                    "offer": sup_offer,
                    "failed": sup_failed,
                    "total": total_sup_interview,
                    "next_round": sup_next_round,
                    "feedback_due": sup_feedback_due
                }
            }
            if total_sup_interview != 0:
                sup_interview["offer"] = int((sup_offer/total_sup_interview) * 100)
                sup_interview["failed"] = int((sup_failed/total_sup_interview) * 100)
                sup_interview["next_round"] = int((sup_next_round/total_sup_interview) * 100)
                sup_interview["feedback_due"] = int((sup_feedback_due/total_sup_interview) * 100)

            guest_interview_qs = Interview.objects.filter(guest=kwargs.get('pk'))
            guest_offer = guest_interview_qs.filter(status='offer').count()
            guest_failed = guest_interview_qs.filter(status='failed').count()
            guest_next_round = guest_interview_qs.filter(status='next_round').count()
            guest_feedback_due = guest_interview_qs.filter(status='feedback_due').count()

            total_guest_interview = guest_interview_qs.count()
            guest_interview = {
                "offer": 0,
                "failed": 0,
                "next_round": 0,
                "feedback_due": 0,
                "count": {
                    "offer": guest_offer,
                    "failed": guest_failed,
                    "total": total_guest_interview,
                    "next_round": guest_next_round,
                    "feedback_due": guest_feedback_due
                }
            }
            if total_guest_interview != 0:
                guest_interview["offer"] = int((guest_offer/total_guest_interview) * 100)
                guest_interview["failed"] = int((guest_failed/total_guest_interview) * 100)
                guest_interview["next_round"] = int((guest_next_round/total_guest_interview) * 100)
                guest_interview["feedback_due"] = int((guest_feedback_due/total_guest_interview) * 100)

            update_qs = ProjectUpdate.objects.filter(
                project__support__support=kwargs.get('pk')).order_by('project_id').distinct('project_id')
            technology_ls = []
            for obj in update_qs:
                project_obj = obj.project
                if hasattr(project_obj, 'description') and hasattr(project_obj.description, 'technology'):
                    technology_ls.append(project_obj.description.technology)

            technology_ls.remove(None)
            total_technology = len(technology_ls)
            technology = {"count": {"total": total_technology}}
            for item in technology_ls:
                technology[item] = int((technology_ls.count(item)/total_technology) * 100)
                technology["count"][item] = technology_ls.count(item)

            data = {
                "test": test,
                "project": project,
                "technology": technology,
                "sup_interview": sup_interview,
                "guest_interview": guest_interview,
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, 'error': error}, status=400)
