import inspect
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, CreateModelMixin

from notification.utils import push_notification
from notification.models import FCMDevice, Notification
from consultant.permissions import ConsultantIsAuthenticated
from log1.utils import get_page_limits, write_exception, ERROR_MSG
from consultant.authentication import ConsultantTokenAuthentication
from notification.serializers import NotificationSerializer, NotificationListSerializer, FCMDeviceSerializer


class FCMDeviceViewSet(GenericViewSet, CreateModelMixin):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def create(self, request, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model='user')
            FCMDevice.objects.get_or_create(
                type='web',
                object_id=request.user.id,
                content_type=content_type,
                device_id=request.data.get('fcm_token')
            )
            return Response({"message": "Token Created"}, status=201)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /emp_notify/
class EmployeeNotificationViewSet(ListModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Notification.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = NotificationSerializer

    @classmethod
    def get_classname(cls):
        return cls.__name__

    @never_cache
    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            queryset = Notification.objects.active(request.user, 'user')
            serializer = NotificationListSerializer(queryset[first:last], many=True)
            unread = Notification.objects.unread(request.user, 'user').count()
            return Response({"data": serializer.data, "total": queryset.count(), "unread": unread}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='mark_as_read')
    def mark_as_read(self, request, *args, **kwargs):
        try:
            notification = get_object_or_404(Notification, id=kwargs.get('pk'))
            notification.mark_as_read()
            notification.save()
            return Response({"message": 'read'}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'user')
            return Response({"message": "read"}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='count')
    def count(self, request):
        try:
            queryset = Notification.objects.unread(request.user, 'user')
            total = queryset.count()
            return Response({"count": total}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='push_notification')
    def push_notification(self, request):
        consultant_id = request.query_params.get('consultant_id')
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
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Mobile App Route - /con_notify/
class ConsultantNotificationViewSet(ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    @never_cache
    def list(self, request, *args, **kwargs):
        # first, last = get_page_limits(request)
        try:
            queryset = Notification.objects.active(request.user, 'consultant')
            total = queryset.count()
            # data = queryset[first:last].values(
            data = queryset.values(
                'id', 'description', 'title', 'deleted', 'unread', 'timestamp', 'category', 'target_object_id')
            return Response({"results": data, "total": total}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='count')
    def count(self, request):
        try:
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = queryset.count()
            return Response({"count": total}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_as_delete')
    def mark_as_delete(self, request, *args, **kwargs):
        # first, last = get_page_limits(request)
        try:
            notification = get_object_or_404(Notification, id=kwargs.get('pk'))
            notification.mark_as_deleted()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            # data = queryset[first:last].values(
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_not_delete')
    def mark_not_delete(self, request, *args, **kwargs):
        # first, last = get_page_limits(request)
        try:
            notification = get_object_or_404(Notification, id=kwargs.get('pk'))
            notification.mark_not_deleted()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            # data = queryset[first:last].values(
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='mark_all_delete')
    def mark_all_delete(self, request):
        try:
            Notification.objects.mark_all_as_deleted(request.user, 'consultant')
            return Response({"result": "deleted"}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_name='mark_as_read')
    def mark_as_read(self, request, *args, **kwargs):
        # first, last = get_page_limits(request)
        try:
            notification = get_object_or_404(Notification, id=kwargs.get('pk'))
            notification.mark_as_read()
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = Notification.objects.unread(request.user, 'consultant').count()
            # data = queryset[first:last].values(
            data = queryset.values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                'target_object_id'
            )
            return Response({"result": data, "total": total}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_name='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'consultant')
            return Response({"result": "read"}, status=202)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)
