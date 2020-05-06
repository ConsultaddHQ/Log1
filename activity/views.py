import logging
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin

from legal.models import Petition
from activity.models import Activity, Comment
from activity.serializers import ActivitySerializer, CommentGetSerializer, CommentSerializer

logger = logging.getLogger(__name__)


def create_activity(object_id, model, user, desc, activity_type):
    content_type = ContentType.objects.get(model=model)
    activity = Activity.objects.create(
        user=user,
        desc=desc,
        object_id=object_id,
        content_type=content_type,
        activity_type=activity_type,
    )
    serializer = ActivitySerializer(activity)
    return serializer.data


class ActivityViewSets(RetrieveModelMixin, ListModelMixin):
    queryset = Activity.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ActivitySerializer,
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            activity_id = kwargs.get('pk')
            activity = Activity.objects.filter(id=activity_id, user=request.user)
            if activity:
                serializer = self.serializer_class(activity)
                return Response({"result": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": "No activity found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        object_id = request.query_params.get('object_id')
        try:
            activity = Activity.objects.filter(object_id=object_id, user=request.user)
            serializer = self.serializer_class(activity, many=True)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class PetitionCommentViewSet(GenericViewSet):
    queryset = Activity.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ActivitySerializer,
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get', 'post'], detail=True, url_path='petition_comments')
    def comments(self, request, *args, **kwargs):
        petition_id = kwargs.get('pk')
        if request.method == 'GET':
            try:
                petition = get_object_or_404(Petition, id=petition_id)
                queryset = petition.comments.filter(parent_comment=None)
                serializer = CommentGetSerializer(queryset, many=True)
                return Response({'results': serializer.data}, status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'POST':
            try:
                content_type = ContentType.objects.get(model='petition')
                comment = Comment.objects.create(
                    user=request.user,
                    object_id=petition_id,
                    content_type=content_type,
                    comment_text=request.data['comment_text'],
                    parent_comment_id=request.data['parent_comment'],
                )
                serializer = CommentGetSerializer(comment)
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
