from django.contrib import admin
from activity.models import Activity, Comment
from import_export.admin import ExportActionModelAdmin


@admin.register(Activity)
class ActivityAdmin(ExportActionModelAdmin):
    list_filter = ('activity_type',)
    search_fields = ('user__employee_name', 'activity_type', 'content_type__model')
    list_display = ('id', 'user', 'object_id', 'activity_type', 'content_type')


@admin.register(Comment)
class CommentAdmin(ExportActionModelAdmin):
    list_filter = ('content_type',)
    search_fields = ('user__employee_name', 'content_type__model')
    list_display = ('id', 'user', 'object_id', 'content_type', 'parent_comment')
