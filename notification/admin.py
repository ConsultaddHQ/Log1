from django.contrib import admin
from notification.models import Notification, FCMDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description', 'timestamp', 'category', 'unread', 'deleted')
    search_fields = ('id', 'title')


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('type', 'active', 'date_created', 'device_id')
    search_fields = ('name', 'device_id', 'type')
