import os
import logging
from pyfcm import FCMNotification
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, CreateModelMixin

from notification.serializers import *
from consultant.permissions import ConsultantIsAuthenticated
from consultant.authentication import ConsultantTokenAuthentication

logger = logging.getLogger(__name__)

push_service = FCMNotification(api_key=os.getenv('FCM_SERVER_KEY'))


def create_notification(user_list, data):
    try:
        recipient_content_type = ContentType.objects.get(model=data['recipient_user_type'])
        sender_content_type = ContentType.objects.get(model=data['sender_user_type'])
        target_content_type = ContentType.objects.get(model=data['target_type'])
        for user in user_list:
            Notification.objects.create(
                title=data["title"],
                recipient_object_id=user.id,
                description=data["description"],
                category=data["category"].lower(),
                sender_object_id=data["sender_id"],
                target_object_id=data["target_id"],
                sender_content_type=sender_content_type,
                target_content_type=target_content_type,
                recipient_content_type=recipient_content_type,
            )
        return False
    except Exception as err:
        return err


def push_notification(registration_ids, message_body):
    push_service.notify_multiple_devices(
        registration_ids=registration_ids,
        message_title=message_body['title'],
        message_body=message_body['body'],
        data_message=message_body,
    )


class EmployeeNotificationViewSet(ListModelMixin, UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Notification.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = NotificationSerializer

    @never_cache
    def list(self, request, *args, **kwargs):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size
        try:
            data = Notification.objects.active(request.user, 'user')[first:last].values(
                'id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model', 'target_object_id'
            )
            total = Notification.objects.unread(request.user, 'user').count()
            return Response({"results": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='mark_as_read')
    def mark_as_read(self, request, *args, **kwargs):
        try:
            notification = get_object_or_404(Notification, id=kwargs.get('pk'))
            notification.mark_as_read()
            notification.save()
            return Response({"result": 'read'}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'user')
            return Response({"result": "success"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantNotificationViewSet(ListModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    @never_cache
    def list(self, request, *args, **kwargs):
        # page = int(request.query_params.get("page", 1))
        # page_size = int(request.query_params.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
        try:
            queryset = Notification.objects.active(request.user, 'consultant')
            total = queryset.count()
            # data = queryset[first:last].values(
            data = queryset.values(
                'id', 'description', 'title', 'deleted', 'unread', 'timestamp', 'category', 'target_object_id')
            return Response({"results": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_name='count')
    def count(self, request):
        try:
            queryset = Notification.objects.unread(request.user, 'consultant')
            total = queryset.count()
            return Response({"count": total}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_name='mark_as_delete')
    def mark_as_delete(self, request, *args, **kwargs):
        # page = int(request.query_params.get("page", 1))
        # page_size = int(request.query_params.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
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
            return Response({"result": data, "total": total}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_name='mark_not_delete')
    def mark_not_delete(self, request, *args, **kwargs):
        # page = int(request.query_params.get("page", 1))
        # page_size = int(request.query_params.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
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
            return Response({"result": data, "total": total}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_name='mark_all_delete')
    def mark_all_delete(self, request):
        try:
            Notification.objects.mark_all_as_deleted(request.user, 'consultant')
            return Response({"result": "deleted"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_name='mark_as_read')
    def mark_as_read(self, request, *args, **kwargs):
        # page = int(request.query_params.get("page", 1))
        # page_size = int(request.query_params.get("page_size", 10))
        # last, first = page * page_size, page * page_size - page_size
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
            return Response({"result": data, "total": total}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_name='mark_all_read')
    def mark_all_read(self, request):
        try:
            Notification.objects.mark_all_as_read(request.user, 'consultant')
            return Response({"result": "read"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
