from django.apps import apps
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from .serializers import getGenericSerializer, FrontRefSerializer, DBTableSerializer
from .utils import DFS, get_models_list

from log1.utils import write_exception, ERROR_MSG
from rest_framework.decorators import action
from .models import DBTable, Field, Structure
from log1.utils import write_exception, ERROR_MSG

def get_model_nodes(model):
    response = {}
    flag={}
    all_connect_models = Structure.objects.filter(model_name=model.name).order_by("id").distinct("id")
    model_list=[]
    for db in all_connect_models:
        fields = db.db_table.fields.all().order_by("id").distinct("id")
        model_list.append(db.db_table)
        for field in fields:
            if db.db_table.name in response:
                if field.id not in flag[db.db_table.name]:
                    flag[db.db_table.name].append(field.id)
                    response[db.db_table.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
            else:
                response[db.db_table.name] = []
                flag[db.db_table.name] = []
                flag[db.db_table.name].append(field.id)
                response[db.db_table.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
    return response, model_list, flag          
    
    
class ReportsViewSets(ModelViewSet):
    queryset =  Field.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            return Response({"message": "No Reports found"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        
        
    @action(methods=['get'], detail=False, url_path="db_list")
    def db_list(self, request):
        try:
            db_tables = DBTable.objects.all()
            serializer = DBTableSerializer(db_tables, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


    @action(methods=['get'], detail=False, url_path="table_ref")
    def table_ref(self, request):
        try:
            table = request.GET.get('table')
            app = request.GET.get('app')
            # breakpoint()
            db_table = DBTable.objects.get(name=table, app_name=app)
            fields = Structure.objects.filter(db_table=db_table)
            front_serial = FrontRefSerializer(fields, many=True)
            return Response({"data":front_serial.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        


    @action(methods=['get'], detail=False, url_path="view_details")
    def details(self, request):
        try:
            app = request.GET.get('app')
            table = request.GET.get('table')
            table_instance = DBTable.objects.filter(app_name=app,name=table).first()
            # Doing BFS to extract all table realted data
            if table_instance:
                response, model_list, flag = get_model_nodes(table_instance)
                model_list.append(table_instance)
                while len(model_list) > 0:
                    models = model_list[0]
                    model_list.pop(0)
                    fields = models.fields.all().order_by("id").distinct("id")
                    for field in fields:
                        if field.front_ref:
                            child_model = DBTable.objects.filter(name=field.model_name).order_by("id").distinct("id")
                            if child_model and child_model.first() and not child_model.first().name in response:
                                model_list.append(child_model.first())
                                
                            if models.name in response:
                                if field.id not in flag[models.name]:
                                    response[models.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
                            else:
                                response[models.name] = []
                                flag[models.name] = []
                                response[models.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
                                flag[models.name].append(field.id)
                        else:
                            if models.name in response:
                                if field.id not in flag[models.name]:
                                    response[models.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
                            else:
                                response[models.name] = []
                                flag[models.name] = []
                                flag[models.name].append(field.id)
                                response[models.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})   
            # breakpoint()                    
            return Response({"data":response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        
        
    @action(methods=['get'], detail=False, url_path="return_qury")
    def return_qury(self, request):
        try:
            request_params = request.GET.get('filter_json', None)
            if request_params:
                keys = list(request_params.keys())
                response = {}
                for key in keys:
                    db = DBTable.objects.get(name=key)
                    model = apps.get_model(db.app_name, db.name)
                    objs = model.objects.all()
                    tableSerializer = getGenericSerializer(model, request_params[key])
                    res_data = tableSerializer(objs[0:500], many=True)
                    response = res_data.data
                return Response({"data":response}, status=200)
            return Response({"message": ERROR_MSG, "error": "filter_json not provided"}, status=402)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        
        
    @action(methods=['get'], detail=False, url_path="dict_details")
    def dict_details(self, request):
        try:
            app = request.GET.get('app')
            table = request.GET.get('table')
            table_instance = DBTable.objects.filter(app_name=app,name=table).first()
            back_ref_model_list, back_ref = get_models_list(table_instance)
            
            back_ref_data=[]
            # breakpoint()
            for table_name in back_ref_model_list:
                model = DBTable.objects.filter(name=table_name).first()
                data = DFS(model)
                back_ref_data.append(data)

            front_ref=DFS(table_instance)
            response = {
                "back_ref":back_ref_data,
                "front_ref":front_ref,
            }               
            return Response({"data":response}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
