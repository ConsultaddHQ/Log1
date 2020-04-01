import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin

from constance import config
from consultant.permissions import ConsultantPetitionIsAuthenticated
from consultant.authentication import ConsultantPetitionTokenAuthentication

from legal.models import *
from legal.serializers import *
from utils_app.mailing import send_email
from consultant.models import Consultant
from employee.token import get_token_generator

logger = logging.getLogger(__name__)
TOKEN_GENERATOR_CLASS = get_token_generator()


# Api for Legal Team
class PetitionViewSets(viewsets.ModelViewSet):
    queryset = Petition.objects.all()
    serializer_class = PetitionSerializer
    permission_classes = (IsAuthenticated,)
    get_serializer_class = PetitionGetSerializer
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=True, url_path='doc_types')
    def doc_types(self, request, *args, **kwargs):
        data = dict()
        doc_types = DocumentList.objects.filter(petition_id=kwargs.get('pk'))
        categories = Types.objects.all().order_by('category').distinct('category')
        for category in categories:
            data[category.category] = []
        for i in doc_types:
            if i.doc_type.category:
                data[i.doc_type.category].append({
                    "id": i.doc_type.id,
                    "name": i.doc_type.name,
                    "category": i.doc_type.category,
                    "value": i.doc_type.display_name,
                })
        return Response({"results": data}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='upload_doc')
    def upload_doc(self, request):
        try:
            petition_id = request.data.get('petition')
            file_type = request.data.get('file_type')
            for file in request.FILES.getlist('file'):
                Document.objects.create(
                    file=file,
                    verified=True,
                    creator=request.user,
                    doc_type_id=file_type,
                    petition_id=petition_id,
                )
            documents = Document.objects.filter(petition=petition_id)
            serializer = DocumentURLSerializer(documents, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='verify_doc')
    def verify_doc(self, request):
        try:
            remark = request.data.get('remark')
            petition = request.data.get('petition')
            doc_type_id = request.data.get('file_type')
            verification_status = request.data.get('status')
            documents = Document.objects.filter(petition_id=petition, doc_type_id=doc_type_id)
            if verification_status == 'verified':
                documents.update(verified=True)
            elif verification_status == 'rejected':
                documents.update(verified=False)
            documents.update(remark=remark)
            documents.save()
            serializer = DocumentURLSerializer(documents, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='doc_request')
    def doc_request(self, request, *args, **kwargs):
        try:
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            beneficiary = petition.beneficiary
            petition_type = petition.get_petition_type_display()
            mail_data = {
                # 'to': [beneficiary.email],
                'to': ['siddharth.g@consultadd.com'],
                'cc': [],
                'bcc': ['sarang.m@consultadd.in'],
                'template': '../templates/doc_upload_request.html',
                'subject': f'Your H1B process - Request for documents',
                'context': {
                    'visa': petition_type,
                    'pin': beneficiary.pin,
                    'name': beneficiary.name,
                    'petitioner_name': petition.assigned_to.employee_name,
                    'link': f"{os.environ.get('PETITION_DOMAIN')}/#/?email={beneficiary.email}",
                },
            }
            send_email(mail_data, petition.assigned_to.email)
            petition.status = "doc_request_sent"
            petition.save()
            return Response({
                "result": {"id": petition.id, "status": petition.status, "message": "mail sent"}
            }, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            petition_id = kwargs.get('pk')
            petition = get_object_or_404(Petition, id=petition_id)
            serializer = self.get_serializer_class(petition)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
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
                    Q(beneficiary__name__istartswith=query) |
                    Q(assigned_to__employee_name=query)
                )
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            petition = Petition.objects.filter(beneficiary_id=request.data['consultant'])
            if petition:
                return Response({"error": "already exist"}, status=status.HTTP_400_BAD_REQUEST)
            petition = Petition.objects.create(
                status='assigned',
                created_by=request.user,
                beneficiary_id=request.data['consultant'],
                assigned_to_id=request.data['assigned_to'],
                petition_type=request.data['petition_type'],
                beneficiary_type=request.data['beneficiary_type'],
            )
            for i in Types.objects.exclude(category="Beneficiary Documents from the petitioner"):
                DocumentList.objects.get_or_create(petition=petition, doc_type=i, to_show=True)
            for i in Types.objects.filter(category="Beneficiary Documents from the petitioner"):
                DocumentList.objects.get_or_create(petition=petition, doc_type=i, to_show=False)

            consultant = petition.beneficiary
            consultant.pin = TOKEN_GENERATOR_CLASS.generate_token()
            consultant.visa_petition = True
            consultant.p_is_active = True
            consultant.save()
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

    @action(methods=['get'], detail=False, url_path='doc_types')
    def doc_types(self, request):
        data = dict()
        petition = Petition.objects.filter(beneficiary=request.user, is_active=True)
        if not petition:
            return Response({"error": "Petition not found"}, status=status.HTTP_400_BAD_REQUEST)
        petition_id = petition.first()
        doc_types = DocumentList.objects.filter(to_show=True, petition_id=petition_id)
        categories = Types.objects.all().order_by('category').distinct('category')
        for category in categories:
            data[category.category] = []
        for i in doc_types:
            if i.doc_type.category:
                data[i.doc_type.category].append({
                    "id": i.doc_type.id,
                    "name": i.doc_type.name,
                    "category": i.doc_type.category,
                    "value": i.doc_type.display_name,
                })
        return Response({"results": data}, status=status.HTTP_200_OK)

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
            for file in request.FILES.getlist('file'):
                Document.objects.create(
                    file=file,
                    creator=None,
                    verified=None,
                    doc_type_id=file_type,
                    petition_id=petition_id,
                )
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
