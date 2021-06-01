from django.apps import apps
from rest_framework import serializers

from employee.models import User
from consultant.models import Consultant
from notification.utils import get_parent_model
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
    target = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'description', 'unread', 'timestamp', 'target', 'avatar')

    @staticmethod
    def get_avatar(obj):
        if obj.sender_content_type.model == 'user':
            return User.objects.get(id=obj.sender_object_id).employee_name
        elif obj.sender_content_type.model == 'consultant':
            return Consultant.objects.get(id=obj.sender_object_id).name
        else:
            return 'System'

    @staticmethod
    def get_target(obj):
        payload = None
        if not obj.parent_content_type:
            parent_model = get_parent_model(obj.target_content_type.model)
        else:
            parent_model = obj.parent_content_type.model

        if not parent_model:
            payload = {
                "id": obj.target_object_id,
                "name": obj.target_content_type.model,
                "sub_id": None,
                "sub_name": None,
            }
            return payload

        model_name = obj.target_content_type.model

        if obj.parent_content_type:
            payload = {
                "id": obj.parent_object_id,
                "sub_id": obj.target_object_id,
                "name": obj.parent_content_type.model,
                "sub_name": obj.target_content_type.model
            }
        else:
            model_class = apps.get_model(obj.target_content_type.app_label, model_name)
            target_obj = model_class.objects.filter(id=obj.target_object_id)
            if target_obj:
                if parent_model == 'consultant':
                    payload = {
                        "name": 'consultant',
                        "sub_id": obj.target_object_id,
                        "id": target_obj.first().consultant.id,
                        "sub_name": obj.target_content_type.model
                    }
                elif parent_model == 'submission':
                    payload = {
                        "name": 'submission',
                        "sub_id": obj.target_object_id,
                        "id": target_obj.first().submission.id,
                        "sub_name": obj.target_content_type.model
                    }

            else:
                if parent_model == 'consultant':
                    payload = {
                        "sub_id": None,
                        "name": 'consultant',
                        "sub_name": model_name,
                        "id": obj.target_object_id,
                    }
                elif parent_model == 'submission':
                    payload = {
                        "sub_id": None,
                        "name": 'submission',
                        "sub_name": model_name,
                        "id": obj.target_object_id,
                    }

        return payload
