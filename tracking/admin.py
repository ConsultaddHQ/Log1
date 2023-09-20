from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from tracking.models import Devices, Location

@admin.register(Devices)
class DeviceInfoAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', )
    search_fields = ('id', )

admin.site.register(Location)

