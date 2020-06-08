from django.contrib import admin
from import_export.admin import ExportActionModelAdmin


from .models import CkillerSubmission, CkillerVendorClient


@admin.register(CkillerSubmission)
class CkillerSubmissionAdmin(ExportActionModelAdmin):
    list_display = ('id', 'consultant', 'submission_id', 'job_title', 'job_location', 'employer', 'sub_created',
                    'marketer', 'vendor_client', 'interview', 'marketing_email', 'rate', 'marketing_phone',)
    search_fields = ('id', 'consultant__email', 'submission_id', 'job_title', 'job_location', 'employer', 'marketer')
    actions = ["export_as_csv"]

    def vendor_client(self, obj):
        return ", ".join([
            vendor.name for vendor in obj.vendors.all()
        ])

    vendor_client.short_description = "Vendor/Client"


@admin.register(CkillerVendorClient)
class CkillerVendorClientAdmin(ExportActionModelAdmin):
    list_display = ('id', 'ckiller_sub', 'name', 'address', 'created')
    search_fields = ('id', 'name')
    actions = ["export_as_csv"]
