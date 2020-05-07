from rest_framework import serializers

from activity.models import *
from employee.serializers import UserSerializer


class ActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Activity
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Comment
        fields = '__all__'


class CommentGetSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    child_comment = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'comment_text', 'user', 'parent_comment', 'object_id', 'child_comment')

    def get_child_comment(self, obj):
        return CommentSerializer(obj.child_comments.all(), many=True).data


class ConsultantCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantComment
        fields = ('id', 'comment_text', 'parent_comment', 'object_id', 'user_type', 'user')

    def get_user_type(self, obj):
        return obj.created_by_content_type.model

    def get_user(self, obj):
        if obj.created_by_content_type.model == 'user':
            name = obj.created_by_content_object.employee_name
        elif obj.created_by_content_type.model == 'consultant':
            name = obj.created_by_content_object.name
        else:
            return None

        result = {
            "employee_name": name,
            "id": obj.created_by_content_object.id,
            "email": obj.created_by_content_object.email
        }
        return result


class ConsultantCommentGetSerializer(serializers.ModelSerializer):
    child_comment = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantComment
        fields = ('id', 'comment_text', 'parent_comment', 'object_id', 'user_type', 'user', 'child_comment')

    def get_child_comment(self, obj):
        return ConsultantCommentSerializer(obj.child_comments.all(), many=True).data

    def get_user_type(self, obj):
        return obj.created_by_content_type.model

    def get_user(self, obj):
        if obj.created_by_content_type.model == 'user':
            name = obj.created_by_content_object.employee_name
        elif obj.created_by_content_type.model == 'consultant':
            name = obj.created_by_content_object.name
        else:
            return None

        result = {
            "employee_name": name,
            "id": obj.created_by_content_object.id,
            "email": obj.created_by_content_object.email
        }
        return result
