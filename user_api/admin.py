from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from user_api.models import *


# Register your models here.
@admin.register(UserAPIKey)
class UserApiAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('user', 'api_key', 'key_value')
    search_fields = ('user__employee_name',)

    def key_value(self, obj):
        return obj.api_key.api_key

    key_value.short_description = "Key"


@admin.register(TriggerEvent)
class TriggerEventAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('name', 'description', 'content_type', 'object_id_path', 'serializer_path')
    search_fields = ('name',)


@admin.register(WebhookEndpoint)
class TriggerEventAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('name', 'target_url', 'is_active')
    search_fields = ('name',)
