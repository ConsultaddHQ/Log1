import os
from rest_framework import serializers

from attachment.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    @staticmethod
    def get_file_name(obj):
        return os.path.split(obj.attachment_file.name)[1]

    class Meta:
        model = Attachment
        fields = ('id', 'object_id', 'attachment_type', 'file_name')


class AttachmentGetSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    @staticmethod
    def get_file_name(obj):
        return os.path.split(obj.attachment_file.name)[1]

    class Meta:
        model = Attachment
        fields = ('id', 'file_name', 'attachment_type')


class AttachmentURLSerializer(serializers.ModelSerializer):
    file_type = serializers.SerializerMethodField()

    @staticmethod
    def get_file_type(obj):
        if len(os.path.split(obj.attachment_file.name)[1].split('.')) > 1:
            return os.path.split(obj.attachment_file.name)[1].split('.')[1]
        return None

    class Meta:
        model = Attachment
        fields = ('id', 'object_id', 'creator', 'attachment_type', 'attachment_file', 'file_type', 'is_active')
