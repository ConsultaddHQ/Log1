from rest_framework import serializers

from attachment.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        exclude = ('created', 'modified')
