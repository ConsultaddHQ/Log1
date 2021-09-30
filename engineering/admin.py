from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from engineering.models import ProjectSupportStatus, ProjectDescription, ProjectSupportUpdate


@admin.register(ProjectSupportStatus)
class ProjectSupportStatusAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('status', 'is_current')
    list_display = ('id', 'project', 'status', 'is_current', 'start', 'end')
    search_fields = ('id', 'project__consultant__name')


@admin.register(ProjectDescription)
class ProjectDescriptionAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', "project", "description", "technology")
    search_fields = ('id', "project_id", "project__consultant__name")


@admin.register(ProjectSupportUpdate)
class ProjectSupportUpdateAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'update_by', 'description')
    search_fields = ('id', 'project__consultant__name', 'updated_by__employee_name')
