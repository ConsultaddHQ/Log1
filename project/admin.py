from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from project.models import Project, ProjectSupport, TimeSheet, PayrollSchedule


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'submission', 'start_date', 'end_date', 'payment_term', 'invoicing_period', 'city',
                    'client_address', 'vendor_address')
    search_fields = ('consultant__name', 'submission__client', 'submission_created_by__employee_name')
    actions = ["export_as_csv"]


@admin.register(ProjectSupport)
class ProjectSupportAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'project', 'support', 'start', 'end')
    search_fields = ('project__consultant__name', 'status', 'project__submission__client',
                     'project__submission__created_by__employee_name', 'support__employee_name')
    actions = ["export_as_csv"]


@admin.register(TimeSheet)
class TimeSheetAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'project', 'is_active', 'status', 'hours', 'additional_hours', 'start', 'end', 'created')
    search_fields = ('id', 'project__id', 'project__consultant__name', 'project__consultant__email')
    actions = ["export_as_csv"]


@admin.register(PayrollSchedule)
class PayrollScheduleAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    search_fields = ('id', 'pay_period_start', 'pay_period_end', 'processing_date', 'pay_date', 'pay_day')
    actions = ["export_as_csv"]
