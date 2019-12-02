import logging
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin

from attachment.serializers import *

logger = logging.getLogger(__name__)


class AttachmentView(RetrieveModelMixin, CreateModelMixin, GenericViewSet):
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
            query = Attachment.objects.filter(object_id=object_id, content_type=obj_content_type).order_by('-created')
            if attachment_type:
                query = query.filter(attachment_type=attachment_type)
            serializer = self.serializer_class(query, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            content_type = ContentType.objects.get(model=request.data['obj_type'])
            object_id = request.data['object_id']
            attachment = Attachment.objects.create(
                object_id=object_id,
                content_type=content_type,
                attachment_type=request.data['attachment_type'],
                attachment_file=request.FILES.get('file'),
                creator=request.user
            )
            serializer = self.serializer_class(attachment)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
