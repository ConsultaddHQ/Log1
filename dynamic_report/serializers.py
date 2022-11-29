from rest_framework import serializers

from .models import Structure


class FieldInfoSerializer(serializers.ModelSerializer):
    ref = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = ('id', 'field_name', 'type', 'display_name', 'model_name', 'ref')

    @staticmethod
    def get_ref(obj):
        if obj.front_ref:
            fields = Structure.objects.filter(db_table__name=obj.model_name)
            return FieldInfoSerializer(fields, many=True).data

    @staticmethod
    def get_type(obj):
        if obj.field_type:
            return obj.field_type.name
