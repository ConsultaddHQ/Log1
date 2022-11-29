from django.apps import apps
from rest_framework import serializers
from dynamic_report.models import DBTable
from dynamic_report.models import Structure


def getGenericSerializer(model_arg, fields_arg):
    dynamic_fields = []
    field_mapper = {}
    for field in fields_arg:
        if type(field) == dict:
            key = list(field.keys())[0]
            dynamic_fields.append(key)
            field_mapper[key] = field[key]
        else:
            dynamic_fields.append(field)

    class TableSerializer(serializers.ModelSerializer):

        class Meta:
            model = model_arg
            fields = dynamic_fields
        
        def to_representation(self, instance):
            ret = super().to_representation(instance)
            for attr in field_mapper:
                objs = getattr(instance, attr)
                if objs is not None:
                    db_name = str(type(objs)).split(".")[-1].split("'")[0]
                    db = DBTable.objects.get(name=db_name)
                    model = apps.get_model(db.app_name, db.name)
                    getSerializer = getGenericSerializer(model,field_mapper[attr])
                    ret[attr] =  getSerializer(objs).data
                else:
                    ret[attr] =  None
            return ret
            
    return TableSerializer



class FrontRefSerializer(serializers.ModelSerializer):
    ref = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = ('id', 'field_name', 'display_name', 'model_name', 'ref')

    @staticmethod
    def get_ref(obj):
        if obj.front_ref:
            fields = Structure.objects.filter(db_table__name=obj.model_name)
            return FrontRefSerializer(fields, many=True).data
        
        
class DBTableSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DBTable
        fields = ("id", "name", "app_name", "own_property_count")
