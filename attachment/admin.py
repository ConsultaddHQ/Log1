from django.contrib import admin

from .models import Attachment
from utils_app.admin import ExportCsvMixin


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'content_type', 'creator', 'attachment_type', 'content_type')
    search_fields = ('id', 'content_type', 'creator__employee_name', 'attachment_type')
    actions = ["export_as_csv"]
