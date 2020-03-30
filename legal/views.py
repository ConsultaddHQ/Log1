import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin

from constance import config
from consultant.permissions import ConsultantPetitionIsAuthenticated
from consultant.authentication import ConsultantPetitionTokenAuthentication

from utils_app.mailing import send_email
from legal.models import Petition, Document
from employee.token import get_token_generator
from legal.serializers import PetitionSerializer, DocumentSerializer, DocumentURLSerializer

logger = logging.getLogger(__name__)
TOKEN_GENERATOR_CLASS = get_token_generator()


# Api for Legal Team
class PetitionViewSets(GenericViewSet, ListModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = Petition.objects.all()
    serializer_class = PetitionSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=True, url_path='doc_request')
    def doc_request(self, request, *args, **kwargs):
        try:
            password = TOKEN_GENERATOR_CLASS.generate_token()
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            beneficiary = petition.beneficiary
            beneficiary.p_password = password
            beneficiary.visa_petition = True
            beneficiary.p_is_active = True
            beneficiary.save()
            mail_data = {
                # 'to': [beneficiary.email],
                'to': ['sarang.m@consultadd.in'],
                'cc': [],
                'bcc': [],
                'template': '../templates/doc_upload_request.html',
                'subject': f'Upload your H1b Petition Documents',
                'context': {
                    'link': "link",
                    'password': "password",
                    'name': beneficiary.name,
                },
            }
            send_email(mail_data, config.LEGAL)
        except Exception as error:
            return error, "error"

    def list(self, request, *args, **kwargs):
        filter_for = request.query_params.get('filter', 'all')
        query = request.query_params.get('query', None)
        queryset = Petition.objects.filter(is_active=True)
        if filter_for == 'my':
            queryset = queryset.filter(
                Q(created_by=request.user) |
                Q(assigned_to=request.user)
            )
        if query:
            queryset = queryset.filter(
                Q(created_by__employee_name__istartswith=request.user) |
                Q(assigned_to__employee_name=request.user)
            )
        serializer = self.serializer_class(queryset, many=True)
        return Response({"result": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        try:
            petition = Petition.objects.create(
                status='assigned',
                created_by=request.user,
                beneficiary_id=request.data['consultant'],
                assigned_to_id=request.data['assigned_to'],
                petition_type=request.data['petition_type'],
                beneficiary_type=request.data['beneficiary_type'],
            )
            serializer = self.serializer_class(petition)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            serializer = self.serializer_class(petition, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Api for Consultant
class PetitionDocsViewSets(GenericViewSet, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentURLSerializer
    permission_classes = (ConsultantPetitionIsAuthenticated,)
    authentication_classes = (ConsultantPetitionTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            queryset = Petition.objects.filter(beneficiary=request.user, is_active=True)
            if queryset:
                petition = queryset.first()
                serializer = self.serializer_class(petition.documents.all(), many=True)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": "Petition not available"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            petition_id = request.data.get('petition')
            file_type = request.data.get('file_type')
            if request.FILES.getlist('file'):
                for file in request.FILES.getlist('file'):
                    Document.objects.create(
                        file=file,
                        creator=None,
                        verified=False,
                        doc_type=file_type,
                        petition_id=petition_id,
                    )
            else:
                return Response({"error": "File not Found"}, status=status.HTTP_400_BAD_REQUEST)
            documents = Document.objects.filter(petition=petition_id)
            serializer = self.serializer_class(documents, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            document_id = kwargs.get('pk')
            document = get_object_or_404(Document, id=document_id, verified=False)
            document.delete()
            return Response({"result": "File deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
