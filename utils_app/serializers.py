from rest_framework import serializers


class UtilSerializer(serializers.Serializer):
    name = serializers.CharField()
