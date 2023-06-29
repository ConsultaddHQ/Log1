from django.contrib import admin
from import_export.admin import ExportActionModelAdmin
from notification.models import Notification, FCMDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_filter = ('sender_content_type__model', 'recipient_content_type__model', 'target_content_type__model')
    list_display = ('id', 'title', 'description', 'timestamp', 'category', 'unread', 'deleted', 'sender_content_type',
                    'recipient_content_type', 'target_content_type')
    search_fields = ('id', 'title')


@admin.register(FCMDevice)
class FCMDeviceAdmin(ExportActionModelAdmin):
    list_display = ('type', 'active', 'object_id', 'date_created', 'device_id')
    search_fields = ('name', 'device_id', 'type', 'object_id')


@admin.register(UserNotification)
class UserNotificationAdmin(ExportActionModelAdmin):
    list_display = ('id','count', 'user')

