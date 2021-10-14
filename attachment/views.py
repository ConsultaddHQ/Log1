from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, CreateModelMixin, DestroyModelMixin

from project.models import Project
from activity.views import create_activity
from project.utils import get_project_check_list
from log1.utils import write_exception, ERROR_MSG
from utils_app.aws_utils import get_s3_object, presigned_post_url
from attachment.serializers import Attachment, AttachmentSerializer


# Route - /attachment/
class AttachmentView(RetrieveModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        obj_type = request.GET.get("obj_type", None)
        object_id = request.GET.get('object_id', None)
        attachment_type = request.GET.get("type", None)
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
                resume = Attachment.objects.filter(
                    object_id=object_id, content_type=content_type, attachment_type='resume'
                )
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
                return Response({"data": serializer.data, "message": "Attachment uploaded"}, status=201)
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
            content_type = self.request.GET.get('type', None)
            attachment_id = self.request.GET.get('attachment_id', None)
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
                return Response({"message": "Attachment deleted"}, status=202)
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
class AttachmentGetView(RetrieveModelMixin, GenericViewSet, ListModelMixin):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            attachments = []
            extensions = []
            uploadedDocuments = self.queryset.filter(object_id=request.data["project_id"])
            for attachment in uploadedDocuments:
                response, error = get_s3_object(attachment.attachment_file.name)
                attachments.append(response)
                extensions.append(attachment.attachment_file.name.split(".")[-1])
            if error:
                return Response({"message": "Unable to fetch document", "error": response}, status=400)
            return Response({"data": attachments, "file_type": extensions}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def retrieve(self, request, *args, **kwargs):
        try:
            attachment = get_object_or_404(Attachment, id=kwargs.get('pk'))
            response, error = get_s3_object(attachment.attachment_file.name)
            if error:
                return Response({"message": "Unable to fetch document", "error": response}, status=400)
            extension = attachment.attachment_file.name.split(".")[-1]
            return Response({"data": response, "file_type": extension}, status=200)
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
            response, error = presigned_post_url(object_name=object_name)
            if error:
                return Response({"message": "Unable to upload document", "error": response}, status=400)
            return Response({"data": response, "message": "Attachment uploaded"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
