from datetime import datetime, timedelta, date

from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin

from marketing.models import Interview
from project.models import ProjectSupport
from consultant.permissions import ConsultantIsAuthenticated
from log1.utils import get_page_limits, write_exception, ERROR_MSG
from consultant.authentication import ConsultantTokenAuthentication
from notification.models import FCMDevice, Notification, UserNotification
from notification.utils import push_notification, schedule_push_notification
from notification.serializers import NotificationSerializer, NotificationListSerializer, FCMDeviceSerializer


class FCMDeviceViewSet(GenericViewSet, CreateModelMixin):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            fcm_token = request.data.get('fcm_token', None)
            if not fcm_token:
                return Response({"message": "Token not found"}, status=400)
            fcm = FCMDevice.objects.filter(device_id=fcm_token)
            if fcm:
                return Response({"message": "Token already exist"}, status=404)
            content_type = ContentType.objects.get(model='user')
            FCMDevice.objects.get_or_create(
                type='web',
                device_id=fcm_token,
                object_id=request.user.id,
                content_type=content_type,
            )
            return Response({"message": "Token Created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /emp_notify/
class EmployeeNotificationViewSet(ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Notification.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = NotificationSerializer

    @never_cache
    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            model = request.GET.get('model', None)
            queryset = Notification.objects.active(request.user, 'user')
            if model:
                queryset = queryset.filter(
                    Q(parent_content_type__model=model) |
                    Q(target_content_type__model=model)
                )
            serializer = NotificationListSerializer(queryset[first:last], many=True)
            unread = Notification.objects.unread(request.user, 'user').count()
            return Response({"data": serializer.data, "total": queryset.count(), "unread": unread}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='mark_as_read')
    def mark_as_read(self, request, pk):
        try:
            notification = get_object_or_404(Notification, id=pk)
            notification.mark_as_read()
            notification.save()
            return Response({"message": 'read'}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'user')
            return Response({"message": "read"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='count')
    def count(self, request):
        try:
            queryset = Notification.objects.unread(request.user, 'user')
            total = queryset.count()
            return Response({"count": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='push_notification')
    def push_notification(self, request):
        consultant_id = request.GET.get('consultant_id')
        try:
            message_body = {
                "category": "alert",
                "show_in_foreground": True,
                "click_action": "https://app.log1.com",
                "title": "Test Feedback creation alert",
                "body": "Feedback is added by Admin on Consultant Name",
                "data": {
                    'is_read': False,
                    'is_deleted': False,
                    'target': 'consultant',
                    'sub_target': 'feedback',
                    'target_id': consultant_id,
                    'timestamp': str(datetime.now()),
                },
            }
            push_notification([request.user.id], message_body)
            return Response({"message": "done"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='remind_me_later')
    def remind_me_later(self, request):
        try:
            type_list = request.data.get("types", [])
            user_id = request.data.get("user_id", None)
            if not user_id:
                return Response({"user not found"}, status=404)
            if 'interview' in type_list:
                content_type = ContentType.objects.get(model='interview')
                notification = UserNotification.objects.filter(user=user_id, content_type=content_type).first()
                interviews = Interview.objects.filter(status="feedback_due", supervisor=user_id)
                if interviews:
                    notification.is_active = False
                    notification.count += 1
                    notification.save()
                    if notification.count < 4:
                        schedule_push_notification.delay(user_id, notification.count, 'interview')
                else:
                    if notification:
                        notification.delete()

            if 'consultant' in type_list:
                content_type = ContentType.objects.get(model='consultant')
                notification = UserNotification.objects.filter(user=user_id, content_type=content_type).first()
                if notification:
                    notification.is_active = False
                    notification.count += 1
                    notification.save()
                    if notification.count < 4:
                        schedule_push_notification.delay(user_id, notification.count, 'consultant')

            if 'project' in type_list:
                content_type = ContentType.objects.get(model='project')
                notification = UserNotification.objects.filter(user=user_id, content_type=content_type).first()
                if notification:
                    notification.is_active = False
                    notification.count += 1
                    notification.save()
                    if notification.count < 4:
                        schedule_push_notification.delay(user_id, notification.count, 'project')

            return Response({"message": "Notification snoozed for next 2 hours"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='notification_due')
    def notification_due(self, request,pk):
        try:
            interview_content_type = ContentType.objects.get(model='interview')
            project_content_type = ContentType.objects.get(model='project')
            consultant_content_type = ContentType.objects.get(model='consultant')
            notifications = UserNotification.objects.filter(user=pk, is_active=True)
            today = date.today()

            interview_due_list = []
            update_due_list = []
            project_due_list = []

            for notification in notifications:
                if notification.content_type == interview_content_type:
                    interviews = Interview.objects.filter(
                        ~Q(supervisor_feedback__question__form_name='interview') &
                        Q(supervisor=pk, start_time__gte=datetime.strptime("2022-05-04", "%Y-%m-%d"))).exclude(
                        status__in=["cancelled", "next_round", "offer", "failed"]).order_by('id').distinct('id')
                    if interviews:
                        for interview in interviews:
                            feedback_due = {
                                "round": interview.round,
                                "interview_id": interview.id,
                                "schedule": interview.end_time,
                                "consultant": {
                                    "name": interview.submission.consultant_marketing.consultant.name,
                                },
                                "supervisor_detail": {
                                    "supervisor_name": interview.supervisor.employee_name,
                                    "call_given_by": 'Consultant' if interview.supervisor.employee_id == 9999 else 'Interviewee'
                                },
                                "submission": {
                                    "client": interview.submission.client,
                                    "vendor": interview.submission.lead.vendor_company.name,
                                    "job_title": interview.submission.lead.position.name,
                                },

                            }
                            interview_due_list.append(feedback_due)
                    else:
                        notification.delete()

                if notification.content_type == project_content_type:
                    seven_days_ago = today - timedelta(days=7)
                    one_day_ago = today - timedelta(days=1)

                    active_projects = Q(
                        ~Q(project__updates__created__gte=seven_days_ago) &
                        Q(project__support_required=True, start__lte=seven_days_ago,
                          statuses__is_current=True, statuses__frequency__in=['is_active', 'less_active'])
                    )
                    terminated_projects = Q(
                        ~Q(project__updates__created__gte=seven_days_ago),
                        Q(statuses__is_current=True, statuses__created__lte=F('end') - timedelta(days=4),
                          statuses__frequency__in=['terminate', 'handover', 'independent']))

                    training_projects = Q(
                        ~Q(project__updates__created__gte=one_day_ago),
                        Q(statuses__is_current=True, statuses__frequency='training'))

                    project_supports = ProjectSupport.objects.filter(
                        Q(support=pk, is_proxy_support=False) & (active_projects | terminated_projects | training_projects)).exclude(
                        project__updates__created__gte=seven_days_ago).order_by('project__id').distinct('project__id')

                    if project_supports:
                        for project_support in project_supports:
                            update_due = {
                                "project_id": project_support.project.id,
                                "project_status": project_support.project.statuses.filter(
                                    is_current=True).values_list('status', flat=True).first(),
                                "support_status": project_support.statuses.filter(is_current=True).values_list(
                                    'frequency', flat=True).first(),
                                "consultant": {
                                    "name": project_support.project.submission.consultant_marketing.consultant.name,
                                    "id": project_support.project.submission.consultant_marketing.consultant.id,
                                },
                                "submission": {
                                    "client": project_support.project.submission.client,
                                    "job_title": project_support.project.submission.lead.job_title,
                                    "vendor": project_support.project.submission.lead.vendor_company.name,
                                },
                            }
                            update_due_list.append(update_due)
                    else:
                        notification.delete()

                if notification.content_type == consultant_content_type:
                    thirty_days_ago = today - timedelta(days=30)
                    fourteen_days_ago = today - timedelta(days=14)
                    sixty_days_ago = today - timedelta(days=60)

                    active_projects = ~Q(project__feedbacks__created__gte=thirty_days_ago) & Q(
                        project__start_date__lte=sixty_days_ago,
                        statuses__is_current=True,
                        statuses__frequency__in=['active', 'less_active'],
                        project__feedbacks__feedback_type__in=["independent", "2_week", "engineering_issue"])

                    initial_projects = ~Q(project__feedbacks__created__gte=fourteen_days_ago) & Q(
                        project__start_date__gte=thirty_days_ago)

                    project_supports = ProjectSupport.objects.filter(
                        Q(support=pk, project__support_required=True, is_proxy_support=False) &
                        (active_projects | initial_projects)).order_by('project__id').distinct('project__id')

                    if project_supports:
                        for project_support in project_supports:
                            feedback_due = {
                                "id": project_support.project.id,
                                "project_status": project_support.project.statuses.filter(
                                    is_current=True).values_list('status', flat=True).first(),
                                "support_status": project_support.statuses.filter(is_current=True).values_list(
                                    'frequency', flat=True).first(),
                                "consultant": {
                                    "name": project_support.project.consultant.name,
                                    "id": project_support.project.consultant.id,
                                },
                                "submission": {
                                    "client": project_support.project.submission.client,
                                    "job_title": project_support.project.submission.lead.job_title,
                                    "vendor": project_support.project.submission.lead.vendor_company.name,
                                },
                            }

                            project_due_list.append(feedback_due)

                    else:
                        notification.delete()

            data = {
                "project": {
                    "count": sum(notification.count for notification in notifications if
                                 notification.content_type == consultant_content_type),
                    "projects": project_due_list
                },
                "interview": {
                    "count": sum(notification.count for notification in notifications if
                                 notification.content_type == interview_content_type),
                    "interviews": interview_due_list
                },
                "update": {
                    "count": sum(notification.count for notification in notifications if
                                 notification.content_type == project_content_type),
                    "updates": update_due_list
                }
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Mobile App Route - /con_notify/
class ConsultantNotificationViewSet(ListModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @never_cache
    def list(self, request, *args, **kwargs):
        try:
            queryset = Notification.objects.active(request.user, 'consultant')
            total = queryset.count()
            data = queryset.values(
                'id', 'description', 'title', 'deleted', 'unread', 'timestamp', 'category', 'target_object_id')
            return Response({"results": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='count')
    def count(self, request):
        try:
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = queryset.count()
            return Response({"count": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_as_delete')
    def mark_as_delete(self, request, pk):
        try:
            notification = get_object_or_404(Notification, id=pk)
            notification.mark_as_deleted()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_not_delete')
    def mark_not_delete(self, request, pk):
        try:
            notification = get_object_or_404(Notification, id=pk)
            notification.mark_not_deleted()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='mark_all_delete')
    def mark_all_delete(self, request):
        try:
            Notification.objects.mark_all_as_deleted(request.user, 'consultant')
            return Response({"result": "deleted"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_as_read')
    def mark_as_read(self, request, pk):
        try:
            notification = get_object_or_404(Notification, id=pk)
            notification.mark_as_read()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'consultant')
            return Response({"result": "read"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)
