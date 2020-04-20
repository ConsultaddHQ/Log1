import os
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from twilio.rest import Client
from employee.models import Asset
from messaging.models import Message, Conversation
from messaging.serializers import MessageSerializer


class SMSViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Conversation.objects.all()
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path='number_list')
    def number_list(self, request):
        try:
            data = Asset.objects.filter(
                asset_type='number', provider='twilio', owner=request.user, is_deleted=False
            ).values('id', 'number')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            conversation_id = kwargs.get('pk', None)
            messages = Message.objects.filter(conversation=conversation_id).order_by('created')\
                .values('id', 'text', 'created', 'is_sent', 'conversation_id')
            return Response({"results": messages}, status=status.HTTP_200_OK)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            asset_id = request.query_params.get('user1', None)
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            conversations = Conversation.objects.filter(user1=asset) \
                .order_by('messages__conversation', '-messages__created').distinct('messages__conversation')\
                .values('id', 'user2', 'created', 'modified', 'messages__text')
            return Response({"results": conversations}, status=status.HTTP_200_OK)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

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
            twilio_message = client.messages.create(
                    body=body,
                    from_=from_,
                    to=to
                )
            conversation, created = Conversation.objects.get_or_create(user1_id=user1, user2=to)
            message = Message.objects.create(
                text=body,
                is_sent=True,
                conversation=conversation
            )
            conversation.modified = datetime.now()
            conversation.save()
            serializer = self.serializer_class(message)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get', 'post'], detail=False, url_path='receive')
    def receive_sms(self, request):
        try:
            to = request.POST.get('To')
            body = request.POST.get('Body')
            from_ = request.POST.get('From')
            user1 = Asset.objects.filter(number=to).first().id
            conversation, created = Conversation.objects.get_or_create(user1_id=user1, user2=from_)
            Message.objects.create(
                text=body,
                is_sent=False,
                conversation_id=conversation.id
            )
            conversation.modified = datetime.now()
            conversation.save()
            return HttpResponse(status=201)
        except Exception as e:
            print(e)
            return HttpResponse(status=400)
