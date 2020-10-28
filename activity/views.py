import logging
from datetime import datetime
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, CreateModelMixin

from legal.models import Petition
from consultant.models import Consultant
from employee.models import User, tag_users
from activity.models import Activity, Comment
from project.models import Project, TimeSheet
from consultant.views import send_notification
from marketing.models import Submission, Interview
from notification.views import create_notification, push_notification
from activity.serializers import ActivitySerializer, CommentGetSerializer

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
    serializer_class = ActivitySerializer
    permission_classes = (IsAuthenticated,)
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
    serializer_class = ActivitySerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

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
            if model not in models.keys():
                return Response({"error": "Selected Model is not valid"}, status=status.HTTP_400_BAD_REQUEST)

            instance = get_object_or_404(models[model], id=object_id)
            comments = instance.comments.filter(parent_comment=None)
            serializer = CommentGetSerializer(comments.order_by('-created'), many=True)
            return Response({'results': serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        model = request.data.get('model', None)
        try:
            content_type = ContentType.objects.get(model=model)
            comment = Comment.objects.create(
                user=request.user,
                content_type=content_type,
                object_id=request.data['id'],
                comment_text=request.data['comment_text'],
                parent_comment_id=request.data['parent_comment'],
            )
            user_list = []
            tags = request.data.get('tagged_user', [])
            if len(tags) > 0:
                for tag in tags:
                    user = get_object_or_404(User, id=tag)
                    user_list.append(user)
                tag_data = {
                    "model": "comment",
                    "object_id": comment.id,
                    "tags": tags
                }
                tag_users(tag_data)
            if content_type.model == 'consultant':
                consultant = get_object_or_404(Consultant, id=request.data['id'])
                title = f"{request.user.employee_name} tagged you in a comment on {consultant.name}'s profile"
            else:
                title = f"{request.user.employee_name} tagged you in a comment"
            notification_data = {
                'category': 'info',
                'sender_user_type': 'user',
                'target_type': model,
                'recipient_user_type': 'user',
                'description': title,
                'title': title,
                'sender_id': request.user.id,
                'target_id': request.data['id'],
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
                    'target': model,
                    'timestamp': str(datetime.now()),
                    'target_id': request.data['id'],
                },
            }
            object_ids = [user.id for user in user_list]
            push_notification(object_ids, message_body)

            serializer = CommentGetSerializer(comment)
            # notification to consultant poc
            if model == 'consultant':
                consultant = Consultant.objects.get(id=request.data['id'])
                title = f"Comment added on {consultant.name}'s profile by {request.user.employee_name}"
                send_notification(consultant, request.user, title)
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
