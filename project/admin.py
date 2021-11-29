from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from project.models import Project, ProjectSupport, SupportStatus, ProjectStatus, ProjectOrder, TimeSheet, \
    PayrollSchedule, ConsultantFeedback


@admin.register(Project)
class ProjectAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('statuses__status',)
    search_fields = ('id', 'consultant__name', 'submission__client', 'submission__created_by__employee_name')
    list_display = ('id', 'submission', 'start_date', 'end_date', 'consultant', 'rate', 'project_status_display',
                    'client_display', 'vendor_display', 'employer', 'client_address', 'city', 'vendor_address',
                    'is_remote')

    def project_status_display(self, obj):
        statuses = obj.statuses.filter(is_current=True)
        if statuses:
            return statuses.first().status
        return None

    project_status_display.short_description = "Status"

    def client_display(self, obj):
        return obj.submission.client

    client_display.short_description = "Client"

    def vendor_display(self, obj):
        return obj.submission.lead.vendor_company.name

    vendor_display.short_description = "Vendor"


@admin.register(ProjectSupport)
class ProjectSupportAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'support', 'start', 'end')
    search_fields = ('id', 'project__consultant__name', 'project__submission__client', 'support__employee_name',
                     'project__submission__created_by__employee_name')


@admin.register(SupportStatus)
class SupportStatusAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', "support", "frequency", "is_current")
    search_fields = ('id', "frequency", "support__support__employee_name", "support__project__consultant__name")


@admin.register(ProjectStatus)
class ProjectStatusAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('status', 'is_current')
    list_display = ('id', 'project', 'status', 'created', 'is_current')
    search_fields = ('id', 'project__consultant__name', 'status', 'project__submission__client', 'is_current')


@admin.register(ProjectOrder)
class ProjectOrderAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'project', 'field', 'value', 'effective_date', 'created_by')
    search_fields = ('id', 'project__consultant__name', 'project__submission__client', 'effective_date')


@admin.register(TimeSheet)
class TimeSheetAdmin(ExportActionModelAdmin):
    list_filter = ('status',)
    actions = ["export_as_csv"]
    search_fields = ('id', 'project__id', 'project__consultant__name', 'project__consultant__email')
    list_display = ('id', 'project', 'is_active', 'status', 'hours', 'start', 'end', 'submitted_at', 'con_comment')


@admin.register(PayrollSchedule)
class PayrollScheduleAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')


@admin.register(ConsultantFeedback)
class ConsultantFeedbackAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('department', 'feedback_type', 'verdict')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'feedback_type', 'rating', 'created')
    list_display = ('id', 'consultant', 'feedback_type', 'department', 'created_by', 'verdict', 'project')
