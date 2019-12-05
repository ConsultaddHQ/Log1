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

    @staticmethod
    def get_child_comment(self):
        return CommentSerializer(self.child_comments.all(), many=True).data
