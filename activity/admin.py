from django.contrib import admin

from activity.models import Activity, Comment


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'object_id', 'activity_type', 'content_type')
    search_fields = ('user__employee_name', 'activity_type', 'content_type')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'object_id', 'content_type', 'parent_comment')
    search_fields = ('user__employee_name', 'content_type')
