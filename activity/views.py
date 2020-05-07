import logging
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, CreateModelMixin

from consultant.permissions import ConsultantPetitionIsAuthenticated
from consultant.authentication import ConsultantPetitionTokenAuthentication

from legal.models import Petition
from project.models import Project, TimeSheet
from marketing.models import Submission, Interview
from consultant.models import Consultant
from activity.models import Activity, Comment, ConsultantComment
from activity.serializers import ActivitySerializer, ConsultantCommentGetSerializer, CommentGetSerializer

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


class CommentViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin):
    queryset = Activity.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ActivitySerializer,
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        object_id = request.data['id']
        model = request.data['model']
        try:
            content_type = ContentType.objects.get(model=model)
            comment = Comment.objects.create(
                user=request.user,
                object_id=object_id,
                content_type=content_type,
                comment_text=request.data['comment_text'],
                parent_comment_id=request.data['parent_comment'],
            )
            serializer = CommentGetSerializer(comment)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        object_id = kwargs.get('pk')
        model = request.query_params.get('model')
        try:
            models = {
                "project": Project,
                "petition": Petition,
                "interview": Interview,
                "timesheet": TimeSheet,
                "submission": Submission,
                "consultant": Consultant,
            }
            if not models[model]:
                return Response({"error": "Selected Model is not valid"}, status=status.HTTP_400_BAD_REQUEST)
            data = get_object_or_404(models[model], id=object_id)
            queryset = data.comments.filter(parent_comment=None)
            serializer = CommentGetSerializer(queryset, many=True)
            return Response({'results': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class ConsultantCommentViewSet(GenericViewSet, CreateModelMixin):
    queryset = Activity.objects.all()
    permission_classes = (ConsultantPetitionIsAuthenticated,)
    serializer_class = ActivitySerializer,
    authentication_classes = (ConsultantPetitionTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        object_id = request.data['id']
        model = request.data['model']
        user_type = request.data['user_type']
        try:
            content_type = ContentType.objects.get(model=model)
            created_by_content_type = ContentType.objects.get(model=user_type)
            comment = ConsultantComment.objects.create(
                object_id=object_id,
                content_type=content_type,
                comment_text=request.data['comment_text'],
                parent_comment_id=request.data['parent_comment'],
                created_by_id=request.user.id,
                created_by_content_type=created_by_content_type,
            )
            serializer = ConsultantCommentGetSerializer(comment)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        object_id = kwargs.get('pk')
        model = request.query_params.get('model')
        try:
            models = {
                "project": Project,
                "petition": Petition,
                "interview": Interview,
                "timesheet": TimeSheet,
                "submission": Submission,
                "consultant": Consultant,
            }
            if not models[model]:
                return Response({"error": "Selected Model is not valid"}, status=status.HTTP_400_BAD_REQUEST)

            data = get_object_or_404(models[model], id=object_id)
            queryset = data.consultant_comments.filter(parent_comment=None)
            serializer = ConsultantCommentGetSerializer(queryset, many=True)
            return Response({'results': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
