from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from project.models import Project, ProjectSupport, TimeSheet, PayrollSchedule, ProjectStatus


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('consultant__name', 'submission__client', 'submission__created_by__employee_name')
    search_fields = ('consultant__name', 'submission__client', 'submission_created_by__employee_name')
    list_display = ('id', 'submission', 'start_date', 'end_date', 'payment_term', 'invoicing_period', 'client_address',
                    'city', 'vendor_address')


@admin.register(ProjectSupport)
class ProjectSupportAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_display = ('id', 'project', 'support', 'start', 'end')
    list_filter = ('project__consultant__name', 'project__submission__client', 'support__employee_name')
    search_fields = ('project__consultant__name', 'status', 'project__submission__client', 'support__employee_name',
                     'project__submission__created_by__employee_name')


@admin.register(ProjectStatus)
class ProjectStatusAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_display = ('id', 'project', 'status', 'created', 'is_current')
    list_filter = ('project__consultant__name', 'status', 'is_current')
    search_fields = ('project__consultant__name', 'status', 'project__submission__client', 'is_current')


@admin.register(TimeSheet)
class TimeSheetAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('project__consultant__name', 'project__submission__client')
    search_fields = ('id', 'project__id', 'project__consultant__name', 'project__consultant__email')
    list_display = ('id', 'project', 'is_active', 'status', 'hours', 'additional_hours', 'start', 'end', 'created')


@admin.register(PayrollSchedule)
class PayrollScheduleAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    search_fields = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    actions = ["export_as_csv"]
