import os
import time
import boto3
from django.conf import settings
from botocore.exceptions import ClientError
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin

from project.models import Project
from activity.views import create_activity
from utils_app.utils import get_project_check_list
from log1.utils import write_exception, ERROR_MSG, write_info
from attachment.serializers import Attachment, AttachmentSerializer


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
    name = ".".join(key.split('/')[3].split(".")[:-1])
    ext = key.split('/')[3].split(".")[-1]
    folder = key.split('/')[1]
    file_name = f"{folder}/{name}_{time.strftime('%Y%m%d-%H%M%S')}.{ext}"

    if not os.path.exists(f"{settings.BASE_DIR}/media/{folder}"):
        os.mkdir(f"{settings.BASE_DIR}/media/{folder}")

    s3 = boto3.client(
        's3', region_name=os.getenv('AWS_REGION_NAME'),
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
            write_info(message=path + " file does not exist", function='delete_temp_file')


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
        return response
    except ClientError as error:
        write_exception(message=error)
        return None


# Route - /attachment/
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
                queryset = Attachment.objects.filter(
                    object_id=object_id, content_type=obj_content_type, attachment_type=attachment_type
                ).order_by('-created')
            else:
                queryset = Attachment.objects.filter(
                    object_id=object_id, content_type=obj_content_type
                ).order_by('-created')
            serializer = self.serializer_class(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model=request.data['obj_type'])
            object_id = request.data['object_id']
            if content_type.model == 'submission' and request.data['obj_type'] == 'resume':
                resume = Attachment.objects.filter(object_id=object_id, content_type=content_type,
                                                   attachment_type='resume')
                if resume:
                    return Response({"message": "You can't attach multiple resumes"}, status=400)

            attachment = Attachment.objects.create(
                object_id=object_id,
                creator=request.user,
                content_type=content_type,
                attachment_file=request.FILES.get('file'),
                attachment_type=request.data['attachment_type'],
            )
            serializer = self.serializer_class(attachment)

            if content_type.model != 'project':
                return Response({"data": serializer.data}, status=201)
            else:
                project = get_object_or_404(Project, id=object_id)
                check_list = get_project_check_list(project)
                return Response(
                    {"data": serializer.data, "check_list": check_list, "message": "Attachment added"}, status=201
                )
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            content_type = self.request.query_params.get('type', None)
            attachment_id = self.request.query_params.get('attachment_id', None)
            roles = request.user.roles
            if content_type == 'consultant' and ('recruiter' in roles or 'admin' in roles or 'superadmin' in roles):
                attachment = get_object_or_404(Attachment, id=attachment_id)
            else:
                attachment = get_object_or_404(Attachment, id=attachment_id, creator=request.user)

            if attachment.content_type.model != 'project':
                desc = f"{attachment.filename} deleted by {request.user.employee_name}"
                create_activity(attachment_id, 'attachment', request.user, desc, 'deleted')
                attachment.attachment_file.delete(save=False)
                attachment.delete()
                return Response({"data": "deleted"}, status=202)
            else:
                project = get_object_or_404(Project, id=attachment.object_id)
                desc = f"{attachment.filename} deleted by {request.user.employee_name}"
                create_activity(attachment_id, 'project', request.user, desc, 'deleted')
                attachment.attachment_file.delete(save=False)
                attachment.delete()

                check_list = get_project_check_list(project)
                return Response({"check_list": check_list, "message": "Attachment deleted"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /get_attachment/
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
            return Response({"data": url, 'file_type': extension}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='upload')
    def upload(self, request):
        try:
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
            return Response({"data": response, "message": "Attachment uploaded"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
