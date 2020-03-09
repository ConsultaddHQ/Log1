from django.contrib import admin

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_filter = ('content_type',)
    list_display = ('id', 'content_type', 'object_id', 'creator', 'attachment_type')
    search_fields = ('id', 'content_type__model', 'object_id', 'creator__employee_name', 'attachment_type')
