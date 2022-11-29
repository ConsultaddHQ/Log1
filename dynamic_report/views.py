from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from rest_framework.decorators import action
from .models import DBTable, Field, Structure
from log1.utils import write_exception, ERROR_MSG

from .serializers import FieldInfoSerializer


class ReportsViewSets(ModelViewSet):
    queryset = Field.objects.all()
    serializer_class = FieldInfoSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @action(methods=['get'], detail=False, url_path="view_details")
    def details(self, request):
        try:
            app = request.GET.get('app')
            table = request.GET.get('table')
            db_table = DBTable.objects.get(name=table, app_name=app)
            fields = Structure.objects.filter(db_table=db_table)
            front_serial = FieldInfoSerializer(fields, many=True)
            back_references = Structure.objects.filter(
                model_name=db_table.name).values_list('db_table__name', flat=True)
            back_fields = {}
            for ref in back_references:
                back_ref_obj = Structure.objects.filter(db_table__name=ref)
                back_serial = FieldInfoSerializer(back_ref_obj, many=True)
                back_fields[ref] = back_serial.data
            return Response({"Front Ref": front_serial.data, "Back Ref": back_fields}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
