from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from engineering.models import ProjectDescription, ProjectUpdate, TrainingAgenda, TrainingCheckList,Cycle,EngineerPoint


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    list_display = ('id', 'update', 'blocker', 'blocker_resolved', 'project', 'type', 'start', 'end')


@admin.register(ProjectDescription)
class ProjectDescriptionAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'project__consultant__name')
    list_display = ('id', 'project', 'remark', 'description', 'update_by', 'technology', 'timezone')


@admin.register(TrainingAgenda)
class TrainingAgendaAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    list_display = ('id', 'position', 'project', 'status', 'duration', 'assignment_given', 'assignment_submitted',
                    'created_by')


@admin.register(TrainingCheckList)
class TrainingCheckListAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'status')

@admin.register(EngineerPoint)
class EngineerPointListAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    actions = ["export_as_csv"]
    list_display = ('id', 'engineer', 'cycle','is_active')

@admin.register(Cycle)
class CycleListAdmin(ExportActionModelAdmin):
    search_fields = ('id',)
    list_display = ('id', 'start_date', 'end_date','is_current')
