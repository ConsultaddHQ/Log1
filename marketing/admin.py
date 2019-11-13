from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from marketing.models import VendorCompany, VendorContact, Lead, Submission, Interview, VendorLayer


@admin.register(VendorCompany)
class VendorCompanyAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'name', 'created_by', 'vendor_display')
    search_fields = ('id', 'name', 'created_by__employee_name')
    actions = ["export_as_csv"]

    def vendor_display(self, obj):
        return ", ".join([
            child.name for child in obj.vendors.all()
        ])

    vendor_display.short_description = "Vendor"


@admin.register(VendorContact)
class VendorContactAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'name', 'email', 'number', 'company', 'created_by')
    search_fields = ('name', 'email', 'company__name', 'created_by__email', 'created_by__employee_name')
    actions = ["export_as_csv"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'job_title', 'city', 'primary_skill', 'status', 'marketer', 'vendor_company', 'sub_display')
    search_fields = ('job_title', 'status', 'marketer__employee_name', 'vendor_company__name', 'primary_skill')
    actions = ["export_as_csv"]

    def sub_display(self, obj):
        return ", ".join([
            child.consultant.name for child in obj.submission.all()
        ])

    sub_display.short_description = "Submission"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'lead', 'consultant_marketing', 'client', 'rate', 'email', 'marketer_display',
                    'status', 'is_active', 'employer', 'phone', 'screening_display', 'vendor_contact', 'visa_type',
                    'visa_start', 'visa_end', 'linkedin', 'date_of_birth', 'current_city', 'created', 'modified')
    search_fields = ('consultant_marketing__consultant__name', 'lead__marketer__employee_name',
                     'consultant_marketing__consultant__email', 'email', 'client')
    actions = ["export_as_csv"]

    def screening_display(self, obj):
        return ", ".join([
            child.ctb.name for child in obj.screening.all() if child.ctb
        ])

    screening_display.short_description = "Screening"

    def marketer_display(self, obj):
        return obj.lead.marketer.employee_name

    marketer_display.short_description = "Marketer"


@admin.register(VendorLayer)
class VendorLayerAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'level', 'submission', 'vendor_company')
    search_fields = ('vendor_company__name',)
    actions = ["export_as_csv"]


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'round', 'submission', 'supervisor', 'status', 'interview_type', 'start_time', 'end_time',
                    'feedback', 'calendar_id', 'guest_display')
    search_fields = ('submission__consultant__name', 'ctb__employee_name', 'status', 'type', 'calendar_id')
    actions = ["export_as_csv"]

    def guest_display(self, obj):
        return "".join([
            user.name for user in obj.guest.all()
        ])
    guest_display.short_description = "Guest"
