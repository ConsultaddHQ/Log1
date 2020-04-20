from twilio.rest import Client
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
# from twilio.twiml.messaging_response import MessagingResponse
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import *
from django.db.models import Q
from messaging.models import Message, Conversation
from employee.models import Asset
from messaging.serializers import MessageSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication


class SMSViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Conversation.objects.all()
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            contacts = Asset.objects.filter(asset_type='number', owner=request.user, is_deleted=False)\
                .values('id', 'number')
            return Response({"results": {"contacts": contacts}}, status=status.HTTP_200_OK)
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

    @action(methods=['get'], detail=False, url_path='conversation_list')
    def conversation_list(self, request):
        try:
            user1 = request.query_params.get('user1', None)
            conversations = Conversation.objects.filter(user1=user1) \
                .order_by('messages__conversation', '-messages__created').distinct('messages__conversation')\
                .values('id', 'user2', 'created', 'modified', 'messages__text')

            return Response({"results": conversations}, status=status.HTTP_200_OK)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='send')
    def send_sms(self, request):
        try:
            user1 = request.data['user1']
            to = request.data['to']
            body = request.data['message']
            account_sid = 'ACa04cf7c7ba488bcacb62a44fe88c8317'
            auth_token = '92b704195e71f92c5b4fbc3e8201745e'

            from_ = get_object_or_404(Asset, id=user1).number
            client = Client(account_sid, auth_token)
            message = client.messages \
                .create(
                    body=body,
                    from_=from_,
                    to=to
                )
            time = timezone.now()
            conversation = Conversation.objects.filter(user1_id=user1, user2=to).first()
            if conversation:
                conversation.modified = time
                conversation_id = conversation.id
                conversation.save()
            else:
                conversations = Conversation.objects.create(
                    user1_id=user1,
                    user2=to,
                    created=time,
                    modified=time
                )
                conversation_id = conversations.id
            messages = Message.objects.create(
                text=body,
                created=time,
                is_sent=True,
                conversation_id=conversation_id
            )
            serializer = self.serializer_class(messages)
            return Response({"results": serializer.data, "m_sid": message.sid}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get', 'post'], detail=False, url_path='receive')
    def receive_sms(self, request):
        try:
            # resp = MessagingResponse()
            body = request.POST.get('Body')
            to = request.POST.get('To')
            from_ = request.POST.get('From')
            user1 = Asset.objects.filter(number=to).first().id
            time = timezone.now()
            conversation = Conversation.objects.filter(user1_id=user1, user2=from_).first()
            if conversation:
                conversation.modified = time
                conversation_id = conversation.id
                conversation.save()
            else:
                conversations = Conversation.objects.create(
                    user1_id=user1,
                    user2=from_,
                    created=time,
                    modified=time
                )
                conversation_id = conversations.id
            Message.objects.create(
                text=body,
                created=time,
                is_sent=False,
                conversation_id=conversation_id
            )

            # str = f"message is {message} Thanks so much for your message."
            # resp.message(str)
            return HttpResponse(status=201)
        except Exception as e:
            print(e)
            return HttpResponse(status=400)
