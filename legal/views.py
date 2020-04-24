import logging
from datetime import datetime
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin

from consultant.permissions import ConsultantPetitionIsAuthenticated
from consultant.authentication import ConsultantPetitionTokenAuthentication

from legal.models import *
from legal.serializers import *
from utils_app.mailing import send_email
from notification.models import FCMDevice
from employee.token import get_token_generator
from attachment.views import presigned_post_url, get_s3_object
from notification.views import create_notification, push_notification

logger = logging.getLogger(__name__)
TOKEN_GENERATOR_CLASS = get_token_generator()


DOCUMENT_TYPE = {
    "6": 'I94',
    "20": 'MSA',
    "4": 'Visa',
    "1": 'Resume',
    "9": 'Paystub',
    "8": 'Form I20',
    "5": 'Passport',
    "17": 'Timesheet',
    "22": 'Work Order',
    "21": 'Offer Letter',
    "15": 'Client Letter',
    "24": 'Consultadd W2',
    "16": 'Vendor Letter',
    "25": 'LCA Document',
    "26": 'Final Petition',
    "18": 'Insurance Cards',
    "2": 'Degree Certificate',
    "13": 'Experience Letter',
    "3": 'Academic Transcripts',
    "23": 'Employment Agreement',
    "19": 'Social Security Card',
    "11": 'Detailed Job Description',
    "7": 'Previous Approval Notices',
    "14": 'Performance Review Sheet ',
    "12": 'Employment Authorization Card',
}


# Api for Legal Team
class PetitionViewSets(viewsets.ModelViewSet):
    queryset = Petition.objects.all()
    serializer_class = PetitionSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def rejection_mail(self, beneficiary_name, petition, document):
        try:
            to = ['sarang.m@consultadd.com']
            if os.environ.get('ENV') == 'prod':
                to = [petition.beneficiary.email]
            mail_data = {
                'to': to,
                'cc': [],
                'bcc': [],
                'template': '../templates/rejection_email.html',
                'subject': f'Your H1B process - Need correction in documents',
                'context': {
                    'name': beneficiary_name,
                    'remark': document.remark,
                    'doc_type': document.doc_type.name,
                    'petitioner_name': petition.assigned_to.employee_name,
                },
            }
            res = send_email(mail_data, petition.assigned_to.email)
            return res, "ok"
        except Exception as error:
            return error, 'error'

    @action(methods=['get'], detail=True, url_path='doc_types')
    def doc_types(self, request, *args, **kwargs):
        data = dict()
        doc_types = DocumentList.objects.filter(petition_id=kwargs.get('pk'))
        categories = Types.objects.all().order_by('category').distinct('category')
        for category in categories:
            data[category.category] = []
        for i in doc_types:
            documents = Document.objects.filter(petition_id=kwargs.get('pk'), doc_type=i.doc_type)
            if documents:
                document = documents.first()
                remark = document.remark
                if document.verified is None:
                    verify_status = 'in_review'
                else:
                    verify_status = "accepted" if document.verified else "rejected"
            else:
                remark = None
                verify_status = "not_uploaded"
            if i.doc_type.category:
                data[i.doc_type.category].append({
                    "remark": remark,
                    "id": i.doc_type.id,
                    "name": i.doc_type.name,
                    "status": verify_status,
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
            serializer = DocumentSerializer(documents, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='verify_doc')
    def verify_doc(self, request):
        try:
            remark = request.data.get('remark')
            petition_id = request.data.get('petition')
            doc_type_id = request.data.get('file_type')
            verification_status = request.data.get('status')
            documents = Document.objects.filter(petition_id=petition_id, doc_type_id=doc_type_id)
            message = None
            if verification_status == 'accepted':
                documents.update(verified=True)
                documents.update(remark=remark)
            elif verification_status == 'rejected':
                documents.update(verified=False)
                documents.update(remark=remark)
                if documents:
                    petition = documents.first().petition
                    res, error = self.rejection_mail(petition.beneficiary.name, petition, documents.first())
                    if error == 'error':
                        message = str(res)
                    else:
                        message = "mail sent"
            serializer = DocumentSerializer(documents, many=True)
            return Response({"result": serializer.data, "message": message}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True, url_path='doc_request')
    def doc_request(self, request, *args, **kwargs):
        try:
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            beneficiary = petition.beneficiary
            petition_type = petition.get_petition_type_display()
            to = ['sarang.m@consultadd.com']
            if os.environ.get('ENV') == 'prod':
                to = [beneficiary.email]
            mail_data = {
                'to': to,
                'cc': [],
                'bcc': [],
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

    @action(methods=['get'], detail=False, url_path='doc_url')
    def doc_url(self, request, *args, **kwargs):
        try:
            document_id = request.query_params.get('document_id')
            document = get_object_or_404(Document, id=document_id)
            url = get_s3_object(document.file.name)
            return Response({"result": url}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        file_name = request.data['file_name']
        object_id = request.data['object_id']

        object_name = f'media/attachments/visa_petition/{object_id}/{file_name}'
        response = presigned_post_url(object_name=object_name)
        return Response({"result": response}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        try:
            petition_id = kwargs.get('pk')
            petition = get_object_or_404(Petition, id=petition_id)
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get("page_size", 10))
        last, first = page * page_size, page * page_size - page_size

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
            total = queryset.count()
            serializer = self.serializer_class(queryset[first:last], many=True)
            return Response({"results": serializer.data, "total": total}, status=status.HTTP_200_OK)
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
                employer=request.data['employer'],
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

    @action(methods=['put'], detail=True, url_path='lca')
    def lca(self, request, *args, **kwargs):
        try:
            petition_id = kwargs.get('pk')
            petition = get_object_or_404(Petition, id=petition_id)
            lca_no = request.data.get('lca_no', None)
            file = request.FILES.get('file', None)
            if petition.status == 'doc_request_sent' and lca_no:
                petition.status = 'lca_filed'
                petition.lca_no = lca_no

            elif petition.status == 'lca_filed' and file:
                Document.objects.create(
                    file=file,
                    verified=True,
                    doc_type_id='25',
                    creator=request.user,
                    petition_id=petition_id,
                )
                petition.status = 'lca_approved'
            else:
                return Response({'error': 'Data is missing'}, status=status.HTTP_400_BAD_REQUEST)

            petition.save()
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)

        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='petition_file')
    def final_petition_file(self, request, *args, **kwargs):
        try:
            petition_id = kwargs.get('pk')
            file = request.FILES.get('file')
            request_status = request.data.get('status')
            petition = get_object_or_404(Petition, id=petition_id)

            if petition.status != 'print':
                if file:
                    Document.objects.create(
                        file=file,
                        verified=True,
                        creator=request.user,
                        doc_type_id='26',
                        petition_id=petition_id,
                    )
                    if petition.status == 'lca_approved':
                        petition.status = 'under_review'

                if request_status == 'reviewed' or request_status == 'print':
                    document = Document.objects.filter(petition=petition_id, doc_type_id='26').first()
                    if not document:
                        return Response({"error": "Please upload document before moving further"},
                                        status=status.HTTP_400_BAD_REQUEST)
                petition.status = request_status

            else:
                return Response({"error": "Changes can't be done at this stage"}, status=status.HTTP_400_BAD_REQUEST)

            petition.save()
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Api for Consultant
class PetitionDocsViewSets(GenericViewSet, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = (ConsultantPetitionIsAuthenticated,)
    authentication_classes = (ConsultantPetitionTokenAuthentication,)

    @action(methods=['post'], detail=False, url_path='contact_us')
    def contact_us(self, request):
        try:
            petition = get_object_or_404(Petition, id=request.data['petition_id'], beneficiary=request.user)
            beneficiary = petition.beneficiary
            to = ['sarang.m@consultadd.com']
            if os.environ.get('ENV') == 'prod':
                to = [petition.assigned_to.email]
            mail_data = {
                'to': to,
                'cc': [],
                'bcc': [],
                'template': '../templates/petition_contact_us.html',
                'subject': f'Petition app issue from {request.user.name} :: {str(datetime.now())}',
                'context': {
                    'message': request.data['message'],
                    'name': petition.assigned_to.employee_name,
                    'consultant_name': petition.beneficiary.name,
                    'consultant_email': petition.beneficiary.email,
                },
            }
            send_email(mail_data, beneficiary.email)
            return Response({"result": {"message": "mail sent"}}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='doc_types')
    def doc_types(self, request):
        data = dict()
        petition = Petition.objects.filter(beneficiary=request.user, is_active=True)
        if not petition:
            return Response({"error": "Petition not found"}, status=status.HTTP_400_BAD_REQUEST)
        petition_id = petition.first().id
        doc_types = DocumentList.objects.filter(to_show=True, petition_id=petition_id)
        categories = Types.objects.all().order_by('category').distinct('category')
        for category in categories:
            data[category.category] = []
        for i in doc_types:
            documents = Document.objects.filter(petition_id=petition_id, doc_type=i.doc_type)
            if documents:
                document = documents.first()
                remark = document.remark
                if document.verified is None:
                    verify_status = 'in_review'
                else:
                    verify_status = "accepted" if document.verified else "rejected"
            else:
                remark = None
                verify_status = "not_uploaded"
            if i.doc_type.category:
                data[i.doc_type.category].append({
                    "remark": remark,
                    "id": i.doc_type.id,
                    "name": i.doc_type.name,
                    "status": verify_status,
                    "category": i.doc_type.category,
                    "value": i.doc_type.display_name,
                })
        return Response({"results": data}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='doc_url')
    def doc_url(self, request, *args, **kwargs):
        try:
            document_id = request.query_params.get('document_id')
            document = get_object_or_404(Document, id=document_id, petition__beneficiary=request.user)
            url = get_s3_object(document.file.name)
            return Response({"result": url}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        file_name = request.data['file_name']
        object_id = request.data['object_id']

        object_name = f'media/attachments/visa_petition/{object_id}/{file_name}'
        response = presigned_post_url(object_name=object_name)
        return Response({"result": response}, status=status.HTTP_200_OK)

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
            petition = get_object_or_404(Petition, id=petition_id)

            if file_type in DOCUMENT_TYPE.keys():
                title = f"{DOCUMENT_TYPE[file_type]} uploaded by {petition.beneficiary.name} ({petition.beneficiary.email})"
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
                create_notification([petition.assigned_to], data)

                # Push Notification
                message_body = {
                    "body": title,
                    "title": title,
                    "category": "alert",
                    "show_in_foreground": True,
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "data": {
                        'is_read': False,
                        'is_deleted': False,
                        'target_id': petition_id,
                        'timestamp': str(timezone.now()),
                    },
                }

                registration_ids = list(
                    FCMDevice.objects.filter(object_id=petition.assigned_to.id, content_type__model='user').values_list(
                        'device_id', flat=True))
                push_notification(registration_ids, message_body)

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
