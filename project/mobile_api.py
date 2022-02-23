import os
from datetime import datetime, timedelta

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Max, Subquery, OuterRef

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from django.contrib.contenttypes.models import ContentType
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin

from constance import config
from employee.models import User
from log1.utils import write_exception
from utils_app.mailing import send_email
from utils_app.aws_utils import get_s3_object
from attachment.serializers import Attachment
from consultant.permissions import ConsultantIsAuthenticated
from consultant.authentication import ConsultantTokenAuthentication
from project.models import Project, TimeSheet, PayrollSchedule, ProjectStatus
from project.serializers import TimeSheetSerializer, PayrollScheduleSerializer
from notification.utils import create_notification, push_notification, push_notification_consultant


# API for Mobile App (For Consultants)
# Route - /timesheet/
class TimeSheetViewSets(GenericViewSet, ListModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=False, url_path='history')
    def history(self, request):
        # page = int(request.GET.get("page", 1))
        # page_size = int(request.GET.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
        try:
            project_status = ['joined', 'terminated-resigned', 'completed', 'terminated', 'extended',
                              'terminated-resigned_rate_issue', 'terminated-resigned_location_issue',
                              'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                              'terminated-fired_budget_issue', 'terminated-fired_performance_issue',
                              'terminated-fired_security_issue']

            project_ids = request.user.get_project().filter(
                statuses__status__in=project_status, statuses__is_current=True
            ).order_by('-id').values_list('id', flat=True)

            pending = TimeSheet.objects.filter(project_id__in=project_ids, is_active=True,
                                               status='draft').order_by('start')
            data = [i for i in pending]

            submitted = TimeSheet.objects.filter(
                project_id__in=project_ids, is_active=True,
                status__in=['submitted', 'rejected', 'approved', 'updated']
            ).order_by('-start')
            for i in submitted:
                data.append(i)
            total = len(data)
            serializer = self.serializer_class(data, many=True)
            return Response({"total": total, "result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        # page = int(request.GET.get("page", 1))
        # page_size = int(request.GET.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
        try:
            project_status = ['joined', 'terminated-resigned', 'completed', 'terminated', 'extended',
                              'terminated-resigned_rate_issue', 'terminated-resigned_location_issue',
                              'terminated-resigned_full_time_offer', 'terminated-resigned_technology_issue',
                              'terminated-fired_budget_issue', 'terminated-fired_performance_issue',
                              'terminated-fired_security_issue']
            projects = request.user.get_project().filter(
                Q(statuses__status='joined', statuses__is_current=True)
            ).order_by('-id')
            if not projects:
                projects = request.user.get_project().filter(
                    Q(statuses__status__in=project_status, statuses__is_current=True)
                ).order_by('-id')
            if projects:
                project = projects.first()
                queryset = TimeSheet.objects.filter(project=project, status__in=['draft', 'rejected'],
                                                    is_active=True).order_by('end')
                serializer = self.serializer_class(queryset, many=True)
                return Response({"result": serializer.data}, status=200)
            return Response({"result": "No Weeks"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            screenshot = False
            zero_hours = request.GET.get('zero_hours', None)
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk'), status__in=['draft', 'rejected'],
                                          is_active=True)
            timesheet_id = timesheet.id
            timesheet.status = 'submitted'
            if zero_hours:
                timesheet.hours = 0.0
                timesheet.additional_hours = 0.0
                screenshot = True
            else:
                timesheet.hours = float(request.data.get('hours'))
                timesheet.additional_hours = float(request.data.get('additional_hours'))

            # Uploading Timesheet Screenshots to S3
            try:
                admin_user = User.objects.get(employee_id=2367)
                content_type = ContentType.objects.get(model='timesheet')
                if request.FILES.get('file1', None):
                    Attachment.objects.create(
                        creator=admin_user,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file1'),
                    )
                    screenshot = True
                if request.FILES.get('file2', None):
                    Attachment.objects.create(
                        creator=admin_user,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file2'),
                    )
                    screenshot = True
                if not screenshot:
                    return Response({"error": "Attachment is required"}, status=400)
            except Exception as error:
                write_exception(error, request)
                return Response({"error": str(error)}, status=400)
            timesheet.submitted_at = datetime.now()
            timesheet.save()
            user_list = User.objects.filter(Q(role__name='finance'))
            title = f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}"
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "timesheet",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://log1.app/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'timesheet',
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)
            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data, "timesheet_id": timesheet_id}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None))
            timesheet.status = 'consultant_rejected'
            timesheet.save()
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# API for Mobile App (For Consultants)
# Route - /payroll/
class PayrollScheduleViewSets(ListModelMixin, GenericViewSet):
    queryset = PayrollSchedule.objects.all()
    serializer_class = PayrollScheduleSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            queryset = PayrollSchedule.objects.filter(pay_date__year=datetime.today().year).order_by('id')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


# Route - /test/
class Test(GenericViewSet, ListModelMixin):
    queryset = PayrollSchedule.objects.all()
    serializer_class = PayrollScheduleSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        timesheet = request.GET.get('timesheet')
        device_id = request.GET.get('fcm_token')
        message_body = {
            "category": "rejected",
            "show_in_foreground": True,
            "click_action": "https://log1.app",
            "title": f"Timesheet rejected for week end {str(timesheet)}",
            "body": f"Timesheet rejected for week end {str(timesheet)}",
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target': 'timesheet',
                'target_id': timesheet,
                'timestamp': str(timezone.now()),
            },
        }

        result = push_notification_consultant([device_id], message_body)
        if result:
            return Response({"result": str(result)}, status=200)
        return Response({"result": "Success"}, status=200)


# Route - /timesheet_v2/
class TimeSheetV2ViewSets(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, pk):
        try:
            if pk == 'null' or pk is None:
                return Response({"error": "Project not found"}, status=400)

            pending = TimeSheet.objects.filter(project_id=pk, is_active=True, status='draft').order_by('start')
            data = [i for i in pending]

            submitted = TimeSheet.objects.filter(
                project_id=pk, is_active=True,
                status__in=['submitted', 'rejected', 'approved', 'updated']
            ).order_by('-start')
            for i in submitted:
                data.append(i)
            serializer = self.serializer_class(data, many=True)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['POST'], detail=False, url_path='contact_us')
    def contact_us(self, request):
        message = request.data.get('message')
        contact_type = request.data.get('type')
        phone_type = request.data.get('device_type', None)
        try:
            if contact_type == 'finance':
                to = ['finance@consultadd.com']
                bcc = ['sarang.m@consultadd.com']
                subject = f'Timesheet app issue from {request.user.name} :: {str(datetime.now())}'
            elif contact_type == 'support':
                to = [config.APP_ADMIN, config.TIMESHEET_APP_ADMIN]
                bcc = []
                subject = f'Bug Report from :: {request.user.email} :: {phone_type} :: {str(datetime.now())}'
            else:
                return Response({"result": "Select correct option"}, status=400)

            if os.environ.get('ENV', 'local') != 'prod':
                to = [config.APP_ADMIN, config.TIMESHEET_APP_ADMIN]
                bcc = []
                subject += "Development server"

            mail_data = {
                'to': to,
                'cc': [],
                'bcc': bcc,
                'subject': subject,
                'template': '../templates/timesheet_contact_us.html',
                'context': {
                    "consultant_name": request.user.name,
                    "consultant_email": request.user.email,
                    "message": message,
                },
            }
            send_email(mail_data, 'log1@consultadd.com', request=request)

            user_list = User.objects.filter(role__name='finance')
            title = f"{request.user.name} has Timesheet issue, please check mail."
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "consultant",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://log1.app/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'app_issue',
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)

            return Response({"result": "mail sent"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['PUT'], detail=True, url_path='cancel')
    def cancel_timesheet(self, request, pk):
        try:
            timesheet = get_object_or_404(TimeSheet, id=pk, status__in=['submitted', 'updated'],
                                          project__consultant=request.user)
            timesheet.hours = 0
            timesheet.status = 'draft'
            timesheet.con_comment = None
            timesheet.additional_hours = 0
            timesheet.save()
            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='attachments')
    def attachments(self, request, pk):
        try:
            timesheet = get_object_or_404(TimeSheet, id=pk, project__consultant=request.user)
            attachments = timesheet.attachments.filter(is_active=True)
            data = []
            for attachment in attachments:
                response, error = get_s3_object(attachment.attachment_file.name)
                if error:
                    return Response({"message": "Unable to fetch attachments", "error": response}, status=400)
                extension = attachment.attachment_file.name.split(".")[-1]
                data.append({
                    "id": attachment.id,
                    "file_path": response,
                    "extension": extension,
                    "created": attachment.created,
                    "file_name": attachment.filename,
                })

            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            project_status = ProjectStatus.objects.filter(project=OuterRef('pk'), is_current=True)
            result = Project.objects.filter(
                Q(consultant=request.user, statuses__is_current=True) & (
                        Q(statuses__status='joined') |
                        Q(statuses__status__istartswith='terminated') |
                        Q(statuses__status__in=['complete', 'extended'])
                )
            ).annotate(
                client=F('submission__client'),
                status=Subquery(project_status.values('status')[:1]),
            ).order_by('-start_date').values('id', 'start_date', 'client', 'employer', 'status')
            return Response({'result': result}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            queryset = TimeSheet.objects.filter(
                project=project, status__in=['draft', 'rejected', 'submitted'], is_active=True
            ).order_by('end')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            screenshot = False
            zero_hours = request.GET.get('zero_hours', None)
            timesheet = get_object_or_404(
                TimeSheet, id=kwargs.get('pk', None),
                project__consultant=request.user,
                status__in=['draft', 'rejected', 'submitted'],
                is_active=True,
            )
            timesheet_id = timesheet.id
            hours = float(request.data.get('hours'))
            timesheet.status = 'submitted' if timesheet.status != 'submitted' else 'updated'
            if zero_hours:
                timesheet.hours = 0.0
                timesheet.additional_hours = 0.0
                screenshot = True
            else:
                timesheet.hours = hours if hours < 41.0 else 40.0
                timesheet.additional_hours = 0.0 if hours < 41.0 else hours - 40.0
            timesheet.con_comment = request.data.get('comment')

            # Uploading Timesheet Screenshots to S3
            try:
                admin_user = User.objects.get(employee_id=2367)
                content_type = ContentType.objects.get(model='timesheet')
                if request.FILES.get('file1', None):
                    attachments = Attachment.objects.filter(object_id=timesheet.id, is_active=True,
                                                            attachment_type='timesheet')
                    for attachment in attachments:
                        attachment.is_active = False
                        attachment.save()

                    Attachment.objects.create(
                        creator=admin_user,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file1'),
                    )
                    screenshot = True
                if request.FILES.get('file2', None):
                    Attachment.objects.create(
                        creator=admin_user,
                        object_id=timesheet.id,
                        content_type=content_type,
                        attachment_type='timesheet',
                        attachment_file=request.FILES.get('file2'),
                    )
                    screenshot = True
                if not screenshot:
                    return Response({"error": "Attachment is required"}, status=400)
            except Exception as error:
                write_exception(error, request)
                return Response({"error": str(error)}, status=400)

            timesheet.submitted_at = datetime.now()
            timesheet.save()

            last_timesheet = TimeSheet.objects.filter(project=timesheet.project).aggregate(Max('end'))
            end_date = last_timesheet['end__max']
            new_ts, created = TimeSheet.objects.get_or_create(
                project=timesheet.project,
                start=end_date + timedelta(days=1),
                end=end_date + timedelta(days=7),
            )
            if created:
                new_ts.hours = 0
                new_ts.save()

            user_list = User.objects.filter(Q(role__name='finance'))
            title = f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}"
            data = {
                "title": title,
                "category": "alert",
                "description": title,
                "target_type": "timesheet",
                "target_id": request.user.id,
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "body": title,
                "title": title,
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com/",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'timesheet',
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }

            user_ids = list(user_list.values_list('id', flat=True))
            push_notification(user_ids, message_body)

            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data, "timesheet_id": timesheet_id}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)
