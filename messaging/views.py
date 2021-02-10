import os
import inspect
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Subquery, OuterRef

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin

from twilio.rest import Client
from employee.models import Asset
from api_key.permissions import APIKey
from log1.utils import write_exception
from messaging.models import Message, Conversation
from notification.views import create_notification, push_notification
from messaging.serializers import MessageSerializer, ConversationSerializer


class SMSViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Conversation.objects.all()
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    @action(methods=['get'], detail=False, url_path='number_list')
    def number_list(self, request):
        try:
            data = Asset.objects.filter(
                asset_type='number', provider='twilio', owner=request.user, is_deleted=False
            ).values('id', 'number')
            return Response({"results": data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({'error': str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            conversation_id = kwargs.get('pk', None)
            messages = Message.objects.filter(
                conversation=conversation_id, conversation__user1__owner=request.user
            ).order_by('created')
            data = messages.values('id', 'text', 'created', 'is_sent', 'conversation_id', 'read')
            messages.update(read=True)
            return Response({"results": data}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({'error': str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            asset_id = request.query_params.get('user1', None)
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            messages = Message.objects.filter(conversation=OuterRef('pk'))
            conversations = Conversation.objects.filter(user1=asset).annotate(
                text=Subquery(messages.values('text').order_by('-id')[:1]),
                read=Subquery(messages.values('read').order_by('-id')[:1])
            ).values(
                'id', 'user2', 'created', 'modified', 'text', 'read'
            ).order_by('-id', '-messages__created').distinct('id')
            return Response({"results": conversations}, status=200)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({'error': str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='send')
    def send_sms(self, request):
        try:
            to = request.data['to']
            user1 = request.data['user1']
            body = request.data['message']
            account_sid = os.environ.get('ACCOUNT_SID')
            auth_token = os.environ.get('AUTH_TOKEN')

            from_ = get_object_or_404(Asset, id=request.data['user1']).number
            client = Client(account_sid, auth_token)
            twilio_message = client.messages.create(body=body, from_=from_, to=to)
            if twilio_message.sid:
                conversation, created = Conversation.objects.get_or_create(user1_id=user1, user2=to)
                message = Message.objects.create(text=body, read=True, is_sent=True, conversation=conversation)
                serializer = self.serializer_class(message)
                return Response({"results": serializer.data}, status=200)
            else:
                return Response({"error": "Message not sent, please try again."}, status=400)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"error": str(error)}, status=400)


class ReceiveSMSViewSet(GenericViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

    @action(methods=['get', 'post'], detail=False, url_path='sms')
    def receive_sms(self, request):
        try:
            api_key = request.query_params.get('api_key', None)
            if APIKey.objects.is_valid(api_key):
                to = request.data.get('To')
                body = request.data.get('Body')
                from_ = request.data.get('From')
                user1 = Asset.objects.filter(number=to).first()
                conversation, created = Conversation.objects.get_or_create(user1_id=user1.id, user2=from_)
                Message.objects.create(text=body, read=False, is_sent=False, conversation_id=conversation.id)
                conversation.modified = datetime.now()
                conversation.save()

                # App Notification
                user_list = [user1.owner]
                title = f"New message received from {from_}"

                notification_data = {
                    'category': 'alert',
                    'sender_user_type': 'conversation',
                    'target_type': 'user',
                    'recipient_user_type': 'user',
                    'description': title,
                    'title': title,
                    'sender_id': conversation.id,
                    'target_id': user1.owner.id,
                }
                create_notification(user_list, notification_data)

                # Push Notification
                message_body = {
                    "category": "alert",
                    "show_in_foreground": True,
                    "click_action": "https://app.log1.com",
                    "body": title,
                    "title": title,
                    "data": {
                        'is_read': False,
                        'is_deleted': False,
                        'target': 'user',
                        'timestamp': str(datetime.now()),
                        'target_id': user1.owner.id,
                    },
                }

                object_ids = [user1.owner.id]
                push_notification(object_ids, message_body)

                return HttpResponse(status=201)
            else:
                return HttpResponse(status=401)
        except Exception as error:
            write_exception(message=error, class_name='ReceiveSMSViewSet', function_name='receive_sms')
            return HttpResponse(status=400)
