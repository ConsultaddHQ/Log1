from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from engineering.models import ProjectDescription, ProjectUpdate


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(ExportActionModelAdmin):
    list_display = ('id', 'update', 'blocker', 'project', 'type', 'start', 'end')


@admin.register(ProjectDescription)
class ProjectDescriptionAdmin(ExportActionModelAdmin):
    list_display = ('id', 'project', 'remark', 'description', 'update_by', 'technology')
