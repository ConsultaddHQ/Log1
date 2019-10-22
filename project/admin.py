from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from project.models import Project, ProjectSupport


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'submission', 'start_date', 'end_date', 'status', 'payment_term', 'invoicing_period', 'city',
                    'client_address', 'vendor_address')
    search_fields = ('submission__consultant__name', 'submission__client', 'submission__lead__marketer__employee_name')
    actions = ["export_as_csv"]


@admin.register(ProjectSupport)
class ProjectSupportAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'project', 'support', 'start', 'end')
    search_fields = ('project__submission__consultant__name', 'status', 'project__submission__client',
                     'project__submission__lead__marketer__employee_name', 'support__employee_name')
    actions = ["export_as_csv"]
