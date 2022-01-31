from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from engineering.models import ProjectDescription, ProjectUpdate, TrainingAgenda, TrainingCheckList


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'update', 'blocker', 'blocker_resolved', 'project', 'type', 'start', 'end')


@admin.register(ProjectDescription)
class ProjectDescriptionAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'remark', 'description', 'update_by', 'technology')


@admin.register(TrainingAgenda)
class TrainingAgendaAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'position', 'project', 'status', 'duration', 'assignment_given', 'assignment_submitted',
                    'created_by')


@admin.register(TrainingCheckList)
class TrainingCheckListAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'status')
