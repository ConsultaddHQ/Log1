from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from activity.models import Activity, Comment, ConsultantComment


@admin.register(Activity)
class ActivityAdmin(ExportActionModelAdmin):
    list_filter = ('activity_type', 'content_type__model', 'object_id')
    search_fields = ('user__employee_name', 'activity_type', 'content_type__model')
    list_display = ('id', 'user', 'object_id', 'activity_type', 'content_type')


@admin.register(Comment)
class CommentAdmin(ExportActionModelAdmin):
    list_filter = ('content_type__model',)
    search_fields = ('user__employee_name', 'content_type__model')
    list_display = ('id', 'user', 'comment_text', 'object_id', 'content_type', 'parent_comment')


@admin.register(ConsultantComment)
class ConsultantCommentAdmin(ExportActionModelAdmin):
    list_filter = ('content_type__model', 'created_by_content_type__model')
    search_fields = ('id', 'object_id', 'content_type__model', 'created_by_content_type__model')
    list_display = ('id', 'comment_text', 'object_id', 'content_type', 'parent_comment', 'created_by_id',
                    'created_by_content_type', 'created')
