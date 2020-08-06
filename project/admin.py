from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from project.models import *


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
    search_fields = ('id', 'project__consultant__name', 'status', 'project__submission__client',
                     'support__employee_name', 'project__submission__created_by__employee_name')


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
    actions = ["export_as_csv"]
    list_filter = ('status',)
    search_fields = ('id', 'project__id', 'project__consultant__name', 'project__consultant__email')
    list_display = ('id', 'project', 'is_active', 'status', 'hours', 'additional_hours', 'start', 'end', 'submitted_at',
                    'con_comment')


@admin.register(PayrollSchedule)
class PayrollScheduleAdmin(ExportActionModelAdmin):
    list_display = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    search_fields = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    actions = ["export_as_csv"]


@admin.register(IphoneAppLink)
class IphoneAppLinkAdmin(ExportActionModelAdmin):
    list_filter = ('is_sent',)
    list_display = ('id', 'code', 'sent_on', 'consultant', 'link', 'is_sent')
    search_fields = ('id', 'code', 'link', 'consultant__name')
    actions = ["export_as_csv"]
