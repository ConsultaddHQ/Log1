from django.apps import apps
from rest_framework import serializers
from dynamic_report.models import DBTable
from dynamic_report.models import Structure
from dynamic_report.utils import check_conditions


class FrontRefSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    key = serializers.SerializerMethodField()
    field_type = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = ('id', 'field_name', "title", 'model_name', 'children', 'key', 'field_type')


    @staticmethod
    def get_field_type(obj):
        return obj.field_type.name

    @staticmethod
    def get_key(obj):
        return obj.id

    @staticmethod
    def get_title(obj):
        return obj.display_name

    @staticmethod
    def get_children(obj):
        if obj.front_ref:
            fields = Structure.objects.filter(db_table__name=obj.model_name)
            return FrontRefSerializer(fields, many=True).data
        
        
class DBTableSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DBTable
        fields = ("id", "name", "app_name", "own_property_count")


def getGenericSerializer(model_arg, fields_arg):
    dynamic_fields = []
    field_mapper = {}
    filter_mapper = {}
    
    for field in fields_arg:
        if type(field) == dict:
            key = list(field.keys())[0]
            dynamic_fields.append(key)
            field_mapper[key] = field[key]['data']
            filter_mapper[key] = field[key]['filter']
        else:
            dynamic_fields.append(field)

    class TableSerializer(serializers.ModelSerializer):

        class Meta:
            model = model_arg
            fields = dynamic_fields
            
        def to_representation(self, instance):
            ret = super().to_representation(instance)
            # need to add code here  equ lte get ne
            for _filter in filter_mapper:
                ojs = getattr(instance, _filter)
                for con in filter_mapper[_filter]:
                    # two posiable case for ManyToMany and OneToMany
                    if '_many_to_many_' in str(type(ojs)): 
                        for obj in ojs:
                            # here need to taken care of type of value needs to be equal
                            value = getattr(obj, con['element'])
                            if check_conditions(con,value) == False:
                                return {}
                    else:
                        value = getattr(ojs, con['element'])
                        if check_conditions(con,value) == False:
                            return {}
                        
            for attr in field_mapper:
                objs = getattr(instance, attr)
                if '_many_to_many_' in str(type(objs)): 
                    #check if it's many to many relationship
                    model = objs.__dict__['model']
                    getSerializer = getGenericSerializer(model,field_mapper[attr])
                    ret[attr] =  getSerializer(objs.all(), many=True).data
                elif objs is not None: 
                    #check if it's many to one relationship
                    db_name = str(type(objs)).split(".")[-1].split("'")[0]
                    db = DBTable.objects.get(name=db_name)
                    model = apps.get_model(db.app_name, db.name)
                    getSerializer = getGenericSerializer(model,field_mapper[attr])
                    ret[attr] =  getSerializer(objs).data
                else:
                    ret[attr] =  None  
            return ret
            
    return TableSerializer