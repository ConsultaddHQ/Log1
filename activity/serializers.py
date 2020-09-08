from rest_framework import serializers

from activity.models import *
from employee.serializers import UserSerializer, TaggedUserSerializer


class ActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Activity
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    tagged_user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'

    def get_tagged_user(self, obj):
        return TaggedUserSerializer(obj.tagged_user.all(), many=True).data


class CommentGetSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    child_comment = serializers.SerializerMethodField()
    tagged_user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'comment_text', 'user', 'parent_comment', 'object_id', 'tagged_user', 'child_comment', 'created')

    def get_child_comment(self, obj):
        return CommentSerializer(obj.child_comments.all(), many=True).data

    def get_tagged_user(self, obj):
        return TaggedUserSerializer(obj.tagged_user.all(), many=True).data


class ConsultantCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantComment
        fields = ('id', 'comment_text', 'parent_comment', 'object_id', 'user_type', 'user', 'created')

    def get_user_type(self, obj):
        return obj.created_by_content_type.model

    def get_user(self, obj):
        content_type = obj.created_by_content_type.model
        if content_type == 'user':
            name = obj.created_by_content_object.employee_name
        elif content_type == 'consultant':
            name = obj.created_by_content_object.name
        else:
            return None

        return {
            "employee_name": name,
            "id": obj.created_by_id,
        }


class ConsultantCommentGetSerializer(serializers.ModelSerializer):
    child_comment = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantComment
        fields = ('id', 'comment_text', 'parent_comment', 'object_id', 'user_type', 'user', 'child_comment', 'created')

    def get_child_comment(self, obj):
        return ConsultantCommentSerializer(obj.child_comments.all().order_by('-created'), many=True).data

    def get_user_type(self, obj):
        return obj.created_by_content_type.model

    def get_user(self, obj):
        content_type = obj.created_by_content_type.model
        if content_type == 'user':
            name = obj.created_by_content_object.employee_name
        elif content_type == 'consultant':
            name = obj.created_by_content_object.name
        else:
            return None

        return {
            "employee_name": name,
            "id": obj.created_by_id,
        }
