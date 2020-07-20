import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin

from attachment.serializers import *
from project.models import Project
from activity.views import create_activity

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
        ExpiresIn=3600
    )
    return url


def download_s3_object(key):
    file_name = key.split('/')[1] + "_" + str(datetime.now()) + "_" + key.split('/')[3]
    s3 = boto3.client('s3',
                      region_name=os.getenv('AWS_REGION_NAME'),
                      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                      )
    s3.download_file(os.getenv('AWS_STORAGE_BUCKET_NAME'), f'media/{key}', f'media/{file_name}')
    return f'media/{file_name}'


def delete_temp_file(paths):
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
        else:
            logger.error(path, "The file does not exist")


def presigned_post_url(object_name, fields=None, conditions=None, expiration=3600):
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    s3 = boto3.client(
            's3', region_name=os.getenv('AWS_REGION_NAME'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    try:
        response = s3.generate_presigned_post(
            bucket_name, object_name, Fields=fields, Conditions=conditions, ExpiresIn=expiration
        )
    except ClientError as e:
        logging.error(e)
        return None

    return response


class AttachmentView(RetrieveModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        obj_type = request.query_params.get("obj_type", None)
        object_id = request.query_params.get('object_id', None)
        attachment_type = request.query_params.get("type", None)
        try:
            obj_content_type = ContentType.objects.get(model=obj_type)
            if attachment_type:
                queryset = Attachment.objects.filter(object_id=object_id, content_type=obj_content_type,
                                                     attachment_type=attachment_type).order_by('-created')
            else:
                queryset = Attachment.objects.filter(object_id=object_id, content_type=obj_content_type
                                                     ).order_by('-created')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model=request.data['obj_type'])
            object_id = request.data['object_id']
            if content_type.model == 'submission' and request.data['obj_type'] == 'resume':
                resume = Attachment.objects.filter(object_id=object_id, content_type=content_type,
                                                   attachment_type='resume')
                if resume:
                    return Response({"error": "you can't attache duplicate resume"}, status=status.HTTP_400_BAD_REQUEST)

            attachment = Attachment.objects.create(
                object_id=object_id,
                creator=request.user,
                content_type=content_type,
                attachment_file=request.FILES.get('file'),
                attachment_type=request.data['attachment_type'],
            )
            serializer = self.serializer_class(attachment)

            if content_type.model != 'project':
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            else:
                project = get_object_or_404(Project, id=object_id)

                msa, work_order, s_msa, s_work_order = 0, 0, 0, 0
                client_address, vendor_address, reporting_details = 0, 0, 0

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

                list_status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                                       + reporting_details) / 6 >= 1 else False

                check_list = {
                    "total": 6,
                    "msa": msa,
                    "msa_signed": s_msa,
                    "status": list_status,
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
            attachment = get_object_or_404(Attachment, id=attachment_id, creator=request.user)
            if attachment.content_type.model != 'project':
                desc = f"{attachment.filename} deleted by {request.user.employee_name}"
                create_activity(attachment_id, 'attachment', request.user, desc, 'deleted')
                attachment.attachment_file.delete(save=False)
                attachment.delete()
                return Response({"result": "deleted"}, status=status.HTTP_202_ACCEPTED)
            else:
                project = get_object_or_404(Project, id=attachment.object_id)
                desc = f"{attachment.filename} deleted by {request.user.employee_name}"
                create_activity(attachment_id, 'project', request.user, desc, 'deleted')
                attachment.attachment_file.delete(save=False)
                attachment.delete()

                client_address, vendor_address, reporting_details = 0, 0, 0
                msa, work_order, s_msa, s_work_order = 0, 0, 0, 0

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

                list_status = True if (s_msa + s_work_order + client_address + vendor_address + start_date
                                       + reporting_details) / 6 >= 1 else False

                check_list = {
                    "total": 6,
                    "msa": msa,
                    "status": list_status,
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
            attachment = get_object_or_404(Attachment, id=kwargs.get('pk'))
            url = get_s3_object(attachment.attachment_file.name)
            extension = attachment.attachment_file.name.split(".")[-1]
            return Response({"result": url, 'file_type': extension}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        content_object = ContentType.objects.get(model=request.data['obj_type'])
        file_name = request.data['file_name']
        object_id = request.data['object_id']

        object_name = 'media/attachments/{app}_{model}/{pk}/{filename}'.format(
            app=content_object.app_label,
            model=content_object.model.lower(),
            pk=object_id,
            filename=file_name,
        )
        response = presigned_post_url(object_name=object_name)
        return Response({"result": response}, status=status.HTTP_200_OK)
