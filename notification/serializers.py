from rest_framework import serializers

from employee.models import User
from consultant.models import Consultant
from notification.models import Notification, FCMDevice


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = '__all__'


class NotificationListSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    target_content_type__model = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'description', 'deleted', 'unread', 'timestamp', 'target_content_type__model',
                  'target_object_id', 'avatar')

    def get_avatar(self, obj):
        if obj.sender_content_type.model == 'user':
            return User.objects.get(id=obj.sender_object_id).employee_name
        elif obj.sender_content_type.model == 'consultant':
            return Consultant.objects.get(id=obj.sender_object_id).name
        else:
            return 'System'

    def get_target_content_type__model(self, obj):
        return obj.target_content_type.model
