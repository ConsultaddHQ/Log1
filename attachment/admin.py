from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(ExportActionModelAdmin):
    list_filter = ('content_type',)
    list_display = ('id', 'content_type', 'object_id', 'creator', 'attachment_type')
    search_fields = ('id', 'content_type__model', 'object_id', 'creator__employee_name', 'attachment_type')
