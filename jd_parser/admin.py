from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from .models import JDParser


@admin.register(JDParser)
class ProjectAdmin(ExportActionModelAdmin):
    list_display = ('id', 'jd', 'job_title', 'location', 'created', 'modified')
    search_fields = ('job_title', 'location')
    actions = ["export_as_csv"]
