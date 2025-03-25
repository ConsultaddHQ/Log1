from rest_framework import serializers

from user_api.models import UserAPIKey


class UserApiSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    api_key = serializers.SerializerMethodField()
    class Meta:
        model = UserAPIKey
        fields = ('id', 'user', 'api_key' )

    @staticmethod
    def get_user(obj):
        return {
            "user_id": obj.user_id,
            "name": obj.user.employee_name
        }

    @staticmethod
    def get_api_key(obj):
        return {
            "api_key": obj.api_key.api_key,
            "name": obj.api_key.name,
            "id": obj.api_key.id
        }
