import logging
from datetime import datetime
from django.db.models import Q, F
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from django.contrib.contenttypes.models import ContentType
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin

from project.serializers import *
from utils_app.mailing import send_email
from notification.models import FCMDevice
from consultant.permissions import ConsultantIsAuthenticated
from consultant.authentication import ConsultantTokenAuthentication
from notification.views import create_notification, push_notification

logger = logging.getLogger(__name__)


# API for Mobile App (For Consultants)
class TimeSheetViewSets(GenericViewSet, ListModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=False, url_path='history')
    def history(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
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
            submitted = TimeSheet.objects.filter(project_id__in=project_ids, is_active=True,
                                                 status__in=['submitted', 'rejected']).order_by('-start')
            for i in submitted:
                data.append(i)
            total = len(data)
            serializer = self.serializer_class(data[first:last], many=True)
            return Response({"total": total, "result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            projects = request.user.get_project().filter(
                Q(statuses__status='joined', statuses__is_current=True)
            ).order_by('-id')
            if projects:
                project = projects.first()
                queryset = TimeSheet.objects.filter(project=project, status__in=['draft', 'rejected'],
                                                    is_active=True).order_by('end')
                serializer = self.serializer_class(queryset[first:last], many=True)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            return Response({"result": "No Weeks"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            screenshot = False
            zero_hours = request.query_params.get('zero_hours', None)
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None), status__in=['draft', 'rejected'],
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
                    return Response({"error": "Attachment is required"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
            timesheet.save()
            user_list = User.objects.filter(Q(role__name='finance'))
            data = {
                "title": f"{request.user.name} - {str(timesheet.end)}",
                "category": "alert",
                "target_id": request.user.id,
                "target_type": "consultant",
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
                "description": f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "category": "alert",
                "show_in_foreground": True,
                "title": f"{request.user.name} - {str(timesheet.end)}",
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "body": f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            registration_ids = list(
                FCMDevice.objects.filter(object_id__in=user_ids, content_type__model='user').values_list(
                    'device_id', flat=True))
            push_notification(registration_ids, message_body)

            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data, "timesheet_id": timesheet_id}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None))
            timesheet.status = 'consultant_rejected'
            timesheet.save()
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# API for Mobile App (For Consultants)
class PayrollScheduleViewSets(ListModelMixin, GenericViewSet):
    queryset = PayrollSchedule.objects.all()
    serializer_class = PayrollScheduleSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        queryset = PayrollSchedule.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)


class Test(GenericViewSet, ListModelMixin):
    queryset = PayrollSchedule.objects.all()
    serializer_class = PayrollScheduleSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        timesheet = request.query_params.get('timesheet')
        device_id = request.query_params.get('fcm_token')
        message_body = {
            "category": "rejected",
            "show_in_foreground": True,
            "title": f"Timesheet rejected for week end {str(timesheet)}",
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "body": f"Timesheet rejected for week end {str(timesheet)}",
            "data": {
                'is_read': False,
                'is_deleted': False,
                'target_id': timesheet,
                'timestamp': str(timezone.now()),
            },
        }

        result = push_notification([device_id], message_body)
        if result:
            return Response({"result": str(result)}, status=status.HTTP_200_OK)
        return Response({"result": "Success"}, status=status.HTTP_200_OK)


class ConsultantProjectViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = TimeSheet.objects.all()
    serializer_class = TimeSheetSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            project_id = kwargs.get('pk')
            queryset = TimeSheet.objects.filter(project_id=project_id, is_active=True).order_by('project')
            serializer = self.serializer_class(queryset[first:last], many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False, url_path='contact_us')
    def contact_us(self, request):
        contact_type = request.data.get('type')
        message = request.data.get('message')
        phone_type = request.data.get('phone_type', None)
        try:
            if contact_type == 'finance':
                mail_data = {
                    'to': ['sarang.m@consultadd.com'],
                    'cc': [],
                    'bcc': [],
                    'subject': f'Timesheet app issue from {request.user.name} :: {str(datetime.now())}',
                    'template': '../templates/timesheet_contact_us.html',
                    'context': {
                        "consultant_name": request.user.name,
                        "consultant_email": request.user.email,
                        "message": message,
                    },
                }
                # send_email(mail_data, request.user.email)
            elif contact_type == 'support':
                mail_data = {
                    'to': ['sarang.m@consultadd.com'],
                    'cc': [],
                    'bcc': [],
                    'subject': f'Bug Report from :: {request.user.email} :: {phone_type} :: {str(datetime.now())}',
                    'template': '../templates/timesheet_contact_us.html',
                    'context': {
                        "consultant_name": request.user.name,
                        "consultant_email": request.user.email,
                        "message": message,
                    },
                }
                # send_email(mail_data, request.user.email)
            else:
                return Response({"result": "Select correct option"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"result": "mail sent"}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            result = Project.objects.filter(
                consultant=request.user, statuses__status='joined', statuses__is_current=True).annotate(
                client=F('submission__client'),
                employer=F('submission__employer', )
            ).values('id', 'start_date', 'client', 'employer')
            return Response({'result': result}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            project = get_object_or_404(Project, id=kwargs.get('pk'))
            queryset = TimeSheet.objects.filter(project=project, status__in=['draft', 'rejected'], is_active=True)
            serializer = self.serializer_class(queryset[first:last], many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            screenshot = False
            zero_hours = request.query_params.get('zero_hours', None)
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None), status__in=['draft', 'rejected'],
                                          is_active=True)
            timesheet_id = timesheet.id
            hours = float(request.data.get('hours'))
            timesheet.status = 'submitted'
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
                    return Response({"error": "Attachment is required"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as error:
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
            timesheet.save()

            user_list = User.objects.filter(Q(role__name='finance'))
            data = {
                "title": f"{request.user.name} - {str(timesheet.end)}",
                "category": "alert",
                "target_id": request.user.id,
                "target_type": "consultant",
                "sender_id": request.user.id,
                "recipient_user_type": "user",
                "sender_user_type": "consultant",
                "description": f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}",
            }
            create_notification(user_list, data)

            # Push Notification
            message_body = {
                "category": "alert",
                "show_in_foreground": True,
                "title": f"{request.user.name} - {str(timesheet.end)}",
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "body": f"{request.user.name} submitted timesheet for the week end {str(timesheet.end)}",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target_id': request.user.id,
                    'timestamp': str(timezone.now()),
                },
            }
            user_ids = list(user_list.values_list('id', flat=True))
            registration_ids = list(
                FCMDevice.objects.filter(object_id__in=user_ids, content_type__model='user').values_list(
                    'device_id', flat=True))
            push_notification(registration_ids, message_body)

            serializer = self.serializer_class(timesheet)
            return Response({"result": serializer.data, "timesheet_id": timesheet_id}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            timesheet = get_object_or_404(TimeSheet, id=kwargs.get('pk', None))
            timesheet.status = 'consultant_rejected'
            timesheet.save()
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
