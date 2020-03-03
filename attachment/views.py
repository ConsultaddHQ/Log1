import os
import boto3
import logging
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin

from attachment.serializers import *
from project.models import Project

logger = logging.getLogger(__name__)


def get_s3_object(key):
    s3 = boto3.client(
        's3', region_name=os.getenv('AWS_REGION_NAME'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': os.getenv('AWS_STORAGE_BUCKET_NAME'),
            'Key': f'media/{key}'
        },
        ExpiresIn=60
    )
    return url


class AttachmentView(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model=request.data['obj_type'])
            object_id = request.data['object_id']
            if content_type.model == 'submission':
                resume = Attachment.objects.filter(object_id=object_id, content_type=content_type,
                                                   attachment_type='resume')
                if resume:
                    return Response({"error": "you can't attache duplicate resume"}, status=status.HTTP_400_BAD_REQUEST)

            attachment = Attachment.objects.create(
                object_id=object_id,
                content_type=content_type,
                attachment_type=request.data['attachment_type'],
                attachment_file=request.FILES.get('file'),
                creator=request.user
            )
            serializer = self.serializer_class(attachment)

            if content_type.model != 'project':
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            else:
                project = get_object_or_404(Project, id=object_id)

                msa, client_address, vendor_address, work_order, s_msa, s_work_order, reporting_details = 0, 0, 0, 0, 0, 0, 0

                start_date = 1 if project.start_date else 0

                if project.attachments.filter(attachment_type='msa'):
                    msa = 1

                if project.attachments.filter(attachment_type='work_order'):
                    work_order = 1

                if project.attachments.filter(attachment_type='work_order_msa'):
                    msa, work_order = 1, 1

                if project.attachments.filter(attachment_type='msa_signed'):
                    s_msa = 1

                if project.attachments.filter(attachment_type='work_order_signed'):
                    s_work_order = 1

                if project.attachments.filter(attachment_type='work_order_msa_signed'):
                    s_msa, s_work_order = 1, 1

                if project.client_address and len(project.client_address.strip()) > 0:
                    client_address = 1

                if project.vendor_address and len(project.vendor_address.strip()) > 0:
                    vendor_address = 1

                if project.reporting_details and len(project.reporting_details.strip()) > 0:
                    reporting_details = 1

                check_list = {
                    "total": 6,
                    "msa": msa,
                    "msa_signed": s_msa,
                    "work_order": work_order,
                    "start_date": start_date,
                    "client_address": client_address,
                    "vendor_address": vendor_address,
                    "work_order_signed": s_work_order,
                    "reporting_details": reporting_details
                }

                return Response({"result": serializer.data, "check_list": check_list}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            attachment_id = self.request.query_params.get('attachment_id', None)
            attachment = get_object_or_404(Attachment, id=attachment_id)
            if attachment.content_type.model != 'project':
                attachment.attachment_file.delete(save=False)
                attachment.delete()
                return Response({"result": "deleted"}, status=status.HTTP_202_ACCEPTED)
            else:
                project = get_object_or_404(Project, id=attachment.object_id)
                attachment.attachment_file.delete(save=False)
                attachment.delete()

                msa, client_address, vendor_address, work_order, reporting_details = 0, 0, 0, 0, 0

                start_date = 1 if project.start_date else 0

                if project.attachments.filter(attachment_type='msa'):
                    msa = 1

                if project.attachments.filter(attachment_type='work_order'):
                    work_order = 1

                if project.attachments.filter(attachment_type='work_order_msa'):
                    msa, work_order = 1, 1

                if project.client_address and len(project.client_address.strip()) > 0:
                    client_address = 1

                if project.vendor_address and len(project.vendor_address.strip()) > 0:
                    vendor_address = 1

                if project.reporting_details and len(project.reporting_details.strip()) > 0:
                    reporting_details = 1

                check_list = {
                    "total": 6,
                    "msa": msa,
                    "start_date": start_date,
                    "work_order": work_order,
                    "client_address": client_address,
                    "vendor_address": vendor_address,
                    "reporting_details": reporting_details,
                }

                return Response({"result": "deleted", "check_list": check_list}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class AttachmentGetView(RetrieveModelMixin, GenericViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            attachment = get_object_or_404(Attachment, id=kwargs.get('pk'), creator=request.user)
            url = get_s3_object(attachment.attachment_file.name)
            return Response({"result": url}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
