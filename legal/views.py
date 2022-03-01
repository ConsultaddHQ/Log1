import os
from datetime import datetime
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin

from utils_app.mailing import send_email
from consultant.models import Consultant
from employee.token import get_token_generator
from utils_app.aws_utils import presigned_post_url, get_s3_object
from consultant.permissions import ConsultantPetitionIsAuthenticated
from notification.utils import create_notification, push_notification
from log1.utils import get_page_limits, write_exception, DONT_HAVE_ACCESS
from consultant.authentication import ConsultantPetitionTokenAuthentication
from activity.serializers import ConsultantComment, ConsultantCommentGetSerializer
from legal.models import Types, Petition, Reason, Document, DocumentList, PETITION_TYPES
from legal.serializers import PetitionSerializer, PetitionGetSerializer, PetitionUpdateSerializer, DocumentSerializer, \
    PetitionTypeSerializer

TOKEN_GENERATOR_CLASS = get_token_generator()


# Route - /petition/
class PetitionViewSets(ModelViewSet):
    queryset = Petition.objects.all()
    serializer_class = PetitionSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @staticmethod
    def rejection_mail(beneficiary_name, petition, document, request):
        try:
            to = ['sarang.m@consultadd.com']
            if os.environ.get('ENV') == 'prod':
                to = [petition.beneficiary.email]
            mail_data = {
                'to': to, 'cc': [], 'bcc': [],
                'template': '../templates/rejection_email.html',
                'subject': f'Your H1B process - Need correction in documents',
                'context': {
                    'name': beneficiary_name,
                    'remark': document.remark,
                    'doc_type': document.doc_type.name,
                    'petitioner_name': petition.assigned_to.employee_name,
                },
            }
            res, msg = send_email(mail_data, petition.assigned_to.email, request=request)
            if not msg:
                return res, "error"
            return res, "ok"
        except Exception as error:
            write_exception(message=error)
            return error, 'error'

    def retrieve(self, request, *args, **kwargs):
        try:
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            query = request.GET.get('query', None)
            filter_for = request.GET.get('filter', 'all')
            consultants = Consultant.objects.filter(petitions__is_active=True)
            if filter_for == 'my':
                consultants = consultants.filter(petitions__assigned_to=request.user)
            if query:
                query = query.lstrip().replace(':amp:', '&')
                consultants = consultants.filter(
                    Q(petitions__assigned_to__employee_name=query) |
                    Q(petitions__beneficiary__name__istartswith=query)
                )
            total = consultants.count()
            data = []
            for consultant in consultants.distinct('id')[first:last]:
                petition = consultant.petitions.latest('created')
                data.append({
                    'consultant': {
                        "id": consultant.id,
                        "name": consultant.name,
                        "email": consultant.email,
                    },
                    'id': petition.id,
                    'status': petition.status,
                    'employer': petition.employer,
                    'is_withdraw': petition.is_withdraw,
                    'expiry_date': petition.expiry_date,
                    'is_withdrawn': petition.is_withdrawn,
                    'petition_type': petition.petition_type,
                    'beneficiary_type': petition.beneficiary_type,
                    'assigned_to': petition.assigned_to.employee_name,
                    'uploaded_documents': Document.objects.filter(petition__beneficiary=consultant).exclude(
                        doc_type__name='other').count(),
                    'total_documents': DocumentList.objects.filter(petition__beneficiary=consultant).exclude(
                        doc_type__name='other').count(),
                })
            return Response({"results": data, "total": total}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            petition = Petition.objects.filter(beneficiary_id=request.data['consultant'])
            if petition:
                return Response({"error": "already exist"}, status=400)
            petition = Petition.objects.create(
                status='assigned',
                created_by=request.user,
                employer=request.data['employer'],
                expiry_date=request.data['expiry_date'],
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
            return Response({"result": serializer.data, "message": "Petition Created"}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            petition = get_object_or_404(Petition, id=kwargs.get('pk'))
            serializer = PetitionUpdateSerializer(petition, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = self.serializer_class(petition)
            return Response({"result": serializer.data, "message": "Petition Updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['get'], detail=False, url_path='documents')
    def documents(self, request):
        try:
            data = dict()
            consultant_id = request.GET.get('consultant')
            petition_ids = Petition.objects.filter(beneficiary_id=consultant_id).values('id')
            doc_types = DocumentList.objects.filter(petition_id__in=petition_ids).exclude(doc_type__category="Petition Document")
            categories = Types.objects.exclude(category="Petition Document").order_by('category').distinct('category')
            for category in categories:
                data[category.category] = []
            for i in doc_types:
                documents = Document.objects.filter(petition_id__in=petition_ids, doc_type=i.doc_type)
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
                data[i.doc_type.category].append({
                    "remark": remark,
                    "id": i.doc_type.id,
                    "name": i.doc_type.name,
                    "status": verify_status,
                    "category": i.doc_type.category,
                    "value": i.doc_type.display_name,
                    "docs": DocumentSerializer(documents, many=True).data,
                })
            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='extension')
    def extension(self, request):
        try:
            petition = Petition.objects.create(
                status='assigned',
                created_by=request.user,
                employer=request.data['employer'],
                expiry_date=request.data['expiry_date'],
                beneficiary_id=request.data['consultant'],
                assigned_to_id=request.data['assigned_to'],
                petition_type=request.data['petition_type'],
                beneficiary_type=request.data['beneficiary_type'],
            )

            for i in Types.objects.filter(category="Petition Document"):
                DocumentList.objects.get_or_create(petition=petition, doc_type=i, to_show=False)

            return Response({"message": "Extension created", "data": {
                "petition": petition.id, "status": petition.status
            }}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='types')
    def types(self, request):
        try:
            consultant_id = request.GET.get('consultant')
            petitions = Petition.objects.filter(beneficiary_id=consultant_id)
            serializer = PetitionTypeSerializer(petitions, many=True)
            return Response({"result": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='employer')
    def employer(self, request):
        try:
            data = ['Consultadd', 'NetResolute', 'Pythonwise', 'Zioqu']
            return Response({"result": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='petition_types')
    def petition_types(self, request):
        try:
            return Response({"result": PETITION_TYPES}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='upload_doc')
    def upload_doc(self, request):
        try:
            consultant_id = request.GET.get('consultant')
            consultant = get_object_or_404(Consultant, id=consultant_id)
            petition_id = consultant.petitions.last().id
            file_type = request.data.get('file_type')
            for file in request.FILES.getlist('file'):
                Document.objects.create(
                    file=file,
                    verified=True,
                    creator=request.user,
                    doc_type_id=file_type,
                    petition_id=petition_id,
                )
            documents = Document.objects.filter(petition=petition_id).exclude(doc_type__category='Petition Document')
            serializer = DocumentSerializer(documents, many=True)
            return Response({"result": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

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
                    res, error = self.rejection_mail(petition.beneficiary.name, petition, documents.first(), request)
                    if error == 'error':
                        message = str(res)
                    else:
                        message = "mail sent"
            serializer = DocumentSerializer(documents, many=True)
            return Response({"result": serializer.data, "message": message}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=True, url_path='doc_request')
    def doc_request(self, request, pk):
        try:
            petition = get_object_or_404(Petition, id=pk)
            beneficiary = petition.beneficiary
            petition_type = petition.get_petition_type_display()
            if os.environ.get('ENV') == 'prod':
                to = [beneficiary.email]
            else:
                to = ['sarang.m@consultadd.com']
            mail_data = {
                'to': to, 'cc': [], 'bcc': [],
                'template': '../templates/doc_upload_request.html',
                'subject': f'Your H1B process - Request for documents',
                'context': {
                    'visa': petition_type,
                    'pin': beneficiary.pin,
                    'name': beneficiary.name,
                    'petitioner_name': petition.assigned_to.employee_name,
                    'link': f"https://{os.environ.get('PETITION_DOMAIN')}/#/?email={beneficiary.email}",
                },
            }
            send_email(mail_data, petition.assigned_to.email, request=request)
            petition.status = "doc_request_sent"
            petition.save()
            return Response({
                "result": {"id": petition.id, "status": petition.status, "message": "mail sent"}
            }, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='doc_url')
    def doc_url(self, request):
        try:
            document_id = request.GET.get('document_id')
            document = get_object_or_404(Document, id=document_id)
            response, error = get_s3_object(document.file.name)
            if error:
                return Response({"message": "Unable to fetch document", "error": response}, status=400)
            return Response({"result": response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        try:
            file_name = request.data['file_name']
            object_id = request.data['object_id']
            object_name = f'media/attachments/visa_petition/{object_id}/{file_name}'
            response, error = presigned_post_url(object_name=object_name)
            if error:
                return Response({"message": "Unable to upload recording", "error": response}, status=400)
            return Response({"result": response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='lca')
    def lca(self, request, pk):
        try:
            petition = get_object_or_404(Petition, id=pk)
            lca_no = request.data.get('lca_no', None)
            file = request.FILES.get('file', None)
            if lca_no:
                petition.lca_no = lca_no
                petition.save()

            elif file:
                Document.objects.create(
                    file=file,
                    verified=True,
                    petition_id=pk,
                    doc_type_id='25',
                    creator=request.user,
                )
            else:
                return Response({'error': 'Data is missing'}, status=400)

            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='petition_file')
    def final_petition_file(self, request, pk):
        try:
            file = request.FILES.get('file')
            request_status = request.data.get('status')
            doc_type_id = request.data.get('doc_type')
            petition = get_object_or_404(Petition, id=pk)

            if file:
                Document.objects.create(
                    file=file,
                    verified=True,
                    petition_id=pk,
                    creator=request.user,
                    doc_type_id=doc_type_id,
                )

            if request_status in ['reviewed', 'print']:
                document = Document.objects.filter(petition_id=pk, doc_type_id='26').first()
                if not document:
                    return Response({"error": "Please upload document before moving further"},
                                    status=400)
            if request_status in ['under_review', 'reviewed', 'print']:
                petition.status = request_status
                petition.save()
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='petition_status')
    def petition_shipping_status(self, request, pk):
        try:
            file = request.FILES.get('file')
            rfe_doc = request.FILES.get('rfe_doc')
            fedex_no = request.data.get('fedex_no')
            reason = request.data.get('reason', None)
            receipt_no = request.data.get('receipt_no')
            request_status = request.data.get('status')
            denied_doc = request.FILES.get('denied_doc')
            approved_doc = request.FILES.get('approved_doc')

            petition = get_object_or_404(Petition, id=pk)
            if petition.status == 'print' and request_status == 'shipped':
                if fedex_no:
                    petition.fedex_no = fedex_no
                else:
                    return Response({"error": "Data is missing"}, status=400)

            elif petition.status == 'shipped' and request_status == 'doc_acknowledged':
                if file and receipt_no:
                    Document.objects.create(
                        file=file,
                        verified=True,
                        petition_id=pk,
                        doc_type_id='27',
                        creator=request.user,
                    )
                    petition.uscis_no = receipt_no
                else:
                    return Response({"error": "Data is missing"}, status=400)

            elif rfe_doc:
                Document.objects.create(
                    file=rfe_doc,
                    verified=True,
                    petition_id=pk,
                    doc_type_id='28',
                    creator=request.user,
                )

            elif petition.status == 'rfe' and request_status == 'rfe_responded':
                if file:
                    Document.objects.create(
                        file=file,
                        verified=True,
                        petition_id=pk,
                        doc_type_id='29',
                        creator=request.user,
                    )
                else:
                    return Response({"error": "File is missing"}, status=400)

            elif denied_doc:
                Document.objects.create(
                    file=denied_doc,
                    verified=True,
                    petition_id=pk,
                    doc_type_id='30',
                    creator=request.user,
                )

            elif approved_doc:
                Document.objects.create(
                    verified=True,
                    petition_id=pk,
                    doc_type_id='31',
                    file=approved_doc,
                    creator=request.user,
                )

            if reason:
                Reason.objects.create(
                    reason=reason,
                    petition_id=pk,
                    created_by=request.user,
                    petition_status=request_status,
                )

            petition.status = request_status
            petition.save()
            serializer = PetitionGetSerializer(petition)
            return Response({"result": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['delete'], detail=True, url_path='document')
    def document(self, request, pk):
        try:
            doc_id = request.GET.get('doc_id', None)
            if doc_id:
                petition = get_object_or_404(Petition, id=pk)
                doc = get_object_or_404(Document, id=doc_id)
                doc.delete()
                serializer = PetitionGetSerializer(petition)
                return Response({"result": serializer.data}, status=202)
            return Response({"error": "document id is missing"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get', 'post'], detail=True, url_path='comment')
    def comment(self, request, pk):
        try:
            if request.method == 'GET':
                if not ('legal' in request.user.roles or 'superadmin' in request.user.roles):
                    return Response({"result": DONT_HAVE_ACCESS}, status=403)

                petition = get_object_or_404(Petition, id=pk)
                comments = petition.consultant_comments.filter(parent_comment=None).order_by('-created')
                serializer = ConsultantCommentGetSerializer(comments, many=True)
                return Response({'results': serializer.data}, status=200)

            elif request.method == 'POST':
                if not ('legal' in request.user.roles):
                    return Response({"result": DONT_HAVE_ACCESS}, status=403)
                content_type = ContentType.objects.get(model='petition')
                created_by_content_type = ContentType.objects.get(model='user')
                comment = ConsultantComment.objects.create(
                    object_id=pk,
                    content_type=content_type,
                    created_by_id=request.user.id,
                    created_by_content_type=created_by_content_type,
                    comment_text=request.data['comment_text'],
                    parent_comment_id=request.data['parent_comment'],
                )
                serializer = ConsultantCommentGetSerializer(comment)
                return Response({"result": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=["put"], detail=True, url_path='withdraw')
    def withdraw(self, request, pk):
        try:
            petition = get_object_or_404(Petition, id=pk)
            petition.is_withdrawn = True
            petition.save()
            return Response({"message": "Petition Withdrawn Successfully"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


# Api for Consultant
# Route - /petition_docs/
class PetitionDocsViewSets(GenericViewSet, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = (ConsultantPetitionIsAuthenticated,)
    authentication_classes = (ConsultantPetitionTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            queryset = Petition.objects.filter(beneficiary=request.user, is_active=True)
            if queryset:
                petition = queryset.first()
                serializer = self.serializer_class(petition.documents.all(), many=True)
                return Response({"results": serializer.data}, status=200)
            return Response({"error": "Petition not available"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            petition_id = request.data.get('petition')
            petition = get_object_or_404(Petition, id=petition_id)
            petition_id = petition.beneficiary.petitions.last().id
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

            doc_type = Types.objects.filter(id=file_type).first()
            if doc_type:
                title = f"{doc_type.display_name} uploaded by {petition.beneficiary.name}({petition.beneficiary.email})"
                data = {
                    "title": title,
                    "category": "alert",
                    "description": title,
                    "target_type": "petition",
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
                    "click_action": "https://log1.app",
                    "data": {
                        'is_read': False,
                        'is_deleted': False,
                        'target': 'petition',
                        'target_id': petition_id,
                        'timestamp': str(timezone.now()),
                    },
                }
                push_notification([petition.assigned_to.id], message_body)

            serializer = self.serializer_class(documents, many=True)
            return Response({"result": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            document_id = kwargs.get('pk')
            document = get_object_or_404(Document, id=document_id, verified=False)
            document.delete()
            return Response({"result": "File deleted"}, status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='contact_us')
    def contact_us(self, request):
        try:
            petition = get_object_or_404(Petition, id=request.data['petition_id'], beneficiary=request.user)
            beneficiary = petition.beneficiary
            to = ['sarang.m@consultadd.com']
            if os.environ.get('ENV') == 'prod':
                to = [petition.assigned_to.email]
            mail_data = {
                'to': to, 'cc': [], 'bcc': [],
                'template': '../templates/petition_contact_us.html',
                'subject': f'Petition app issue from {request.user.name} :: {str(datetime.now())}',
                'context': {
                    'message': request.data['message'],
                    'name': petition.assigned_to.employee_name,
                    'consultant_name': petition.beneficiary.name,
                    'consultant_email': petition.beneficiary.email,
                },
            }
            send_email(mail_data, beneficiary.email, request=request)
            return Response({"result": {"message": "mail sent"}}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get', 'post'], detail=True, url_path='comment')
    def comment(self, request, pk):
        try:
            petition = get_object_or_404(Petition, id=pk)
            if petition.beneficiary != request.user:
                return Response({"result": DONT_HAVE_ACCESS}, status=403)

            if request.method == 'GET':
                comments = petition.consultant_comments.filter(parent_comment=None)
                serializer = ConsultantCommentGetSerializer(comments, many=True)
                return Response({'results': serializer.data}, status=200)

            elif request.method == 'POST':
                content_type = ContentType.objects.get(model='petition')
                created_by_content_type = ContentType.objects.get(model='consultant')
                comment = ConsultantComment.objects.create(
                    object_id=pk,
                    content_type=content_type,
                    created_by_id=request.user.id,
                    created_by_content_type=created_by_content_type,
                    comment_text=request.data['comment_text'],
                    parent_comment_id=request.data['parent_comment'],
                )
                # App Notification

                user_list = [petition.created_by, petition.assigned_to]
                title = f"{request.user.name} posted a new comment"

                notification_data = {
                    'title': title,
                    'category': 'alert',
                    'description': title,
                    'target_type': 'user',
                    'sender_id': request.user.id,
                    'recipient_user_type': 'user',
                    'sender_user_type': 'consultant',
                    'target_id': petition.assigned_to.id,
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
                        'target_id': petition.assigned_to.id,
                    },
                }

                object_ids = [petition.created_by.id, petition.assigned_to.id]
                push_notification(object_ids, message_body)

                serializer = ConsultantCommentGetSerializer(comment)
                return Response({"result": serializer.data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='doc_types')
    def doc_types(self, request):
        try:
            data = dict()
            petition = Petition.objects.filter(beneficiary=request.user, is_active=True)
            if not petition:
                return Response({"error": "Petition not found"}, status=400)
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
            return Response({"results": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='doc_url')
    def doc_url(self, request):
        try:
            document_id = request.GET.get('document_id')
            document = get_object_or_404(Document, id=document_id, petition__beneficiary=request.user)
            response, error = get_s3_object(document.file.name)
            if error:
                return Response({"message": "Unable to fetch document", "error": response}, status=400)
            return Response({"result": response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        try:
            file_name = request.data['file_name']
            object_id = request.data['object_id']
            object_name = f'media/attachments/visa_petition/{object_id}/{file_name}'
            response, error = presigned_post_url(object_name=object_name)
            if error:
                return Response({"message": "Unable to upload recording", "error": response}, status=400)
            return Response({"result": response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)
