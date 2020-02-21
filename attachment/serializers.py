import os
from rest_framework import serializers

from attachment.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    def get_file_name(self, obj):
        return os.path.split(obj.attachment_file.name)[1]

    class Meta:
        model = Attachment
        fields = ('id', 'object_id', 'creator', 'attachment_type', 'file_name')
