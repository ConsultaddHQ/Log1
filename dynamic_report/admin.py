from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from .models import Field, DBTable, Structure

# admin.site.register(Field)
# admin.site.register(DBTable)
# admin.site.register(Structure)



@admin.register(Structure)
class ProjectUpdateAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    list_filter = ('db_table', 'front_ref', 'back_ref', 'field_name')
    list_display = ('id','field_name','db_table', 'front_ref', 'back_ref', 'model_name')


@admin.register(DBTable)
class DBTableUpdateAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    
    
@admin.register(Field)
class FieldUpdateAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]