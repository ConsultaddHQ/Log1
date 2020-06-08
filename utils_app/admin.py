import csv
from django.contrib import admin
from django.http import HttpResponse
from import_export.admin import ExportActionModelAdmin

from utils_app.models import City, ScrumMeeting


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        return response

    export_as_csv.short_description = "Export to CSV "


@admin.register(City)
class CityAdmin(ExportActionModelAdmin):
    list_filter = ('state',)
    actions = ["export_as_csv"]
    search_fields = ('name', 'state')
    list_display = ('id', 'name', 'state')


@admin.register(ScrumMeeting)
class ScrumMeetingAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('previous', 'held_on')
    list_display = ('id', 'held_on', 'previous')
