from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from marketing.models import VendorCompany, VendorContact, Lead, Submission, Interview, VendorLayer


@admin.register(VendorCompany)
class VendorCompanyAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('created_by', 'name')
    search_fields = ('id', 'name', 'created_by')
    list_display = ('id', 'name', 'created_by', 'vendor_display')

    def vendor_display(self, obj):
        return ", ".join([
            child.name for child in obj.vendors.all()
        ])

    vendor_display.short_description = "Vendor"


@admin.register(VendorContact)
class VendorContactAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('company__name', 'created_by__employee_name')
    list_display = ('id', 'name', 'email', 'number', 'company', 'created_by')
    search_fields = ('id', 'name', 'email', 'company__name', 'created_by__email', 'created_by__employee_name')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('owner__employee_name', 'vendor_company__name', 'primary_skill')
    search_fields = ('id', 'job_title', 'status', 'owner__employee_name', 'vendor_company__name', 'primary_skill')
    list_display = ('id', 'job_title', 'city', 'primary_skill', 'status', 'owner', 'vendor_company', 'sub_display')

    def sub_display(self, obj):
        return ", ".join([
            child.consultant.name for child in obj.submission.all()
        ])

    sub_display.short_description = "Submission"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    empty_value_display = '-------'
    list_filter = ('consultant_marketing__consultant__name', 'created_by__employee_name', 'status')
    search_fields = ('id', 'consultant_marketing__consultant__name', 'created_by__employee_name', 'email', 'client',
                     'consultant_marketing__consultant__email')
    list_display = ('id', 'lead', 'consultant_marketing', 'client', 'rate', 'email', 'created_by', 'lead_owner_display',
                    'status', 'is_active', 'employer', 'phone', 'screening_display', 'vendor_contact', 'visa_type',
                    'visa_start', 'visa_end', 'linkedin', 'date_of_birth', 'current_city', 'created', 'modified')

    def screening_display(self, obj):
        return ", ".join([
            child.supervisor.employee_name for child in obj.screening.all() if child.supervisor
        ])

    screening_display.short_description = "Screening"

    def lead_owner_display(self, obj):
        if obj.lead.owner:
            return obj.lead.owner.employee_name
        return None

    lead_owner_display.short_description = "Lead Owner"


@admin.register(VendorLayer)
class VendorLayerAdmin(admin.ModelAdmin, ExportCsvMixin):
    actions = ["export_as_csv"]
    list_filter = ('vendor_company__name',)
    search_fields = ('vendor_company__name',)
    list_display = ('id', 'level', 'submission', 'vendor_company')


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin, ExportCsvMixin):
    empty_value_display = '-------'
    actions = ['export_as_csv', 'make_status_feedback_due']
    list_filter = ('submission__consultant_marketing__consultant__name', 'supervisor__employee_name',
                   'submission__created_by__employee_name', 'status')
    search_fields = ('id', 'submission__consultant_marketing__consultant__name', 'supervisor__employee_name',
                     'calendar_id', 'submission__created_by__employee_name')
    list_display = ('id', 'round', 'submission', 'supervisor', 'status', 'screening_type', 'start_time', 'end_time',
                    'interview_mode', 'feedback', 'calendar_id', 'guest_display')

    def guest_display(self, obj):
        return ", ".join([
            user.employee_name for user in obj.guest.all()
        ])
    guest_display.short_description = "Guest"

    def make_status_feedback_due(self, request, queryset):
        rows_updated = queryset.update(status='cancelled')
        if rows_updated == 1:
            message_bit = "1 Interview was"
        else:
            message_bit = "%s Interviews were" % rows_updated
        self.message_user(request, "%s successfully marked as Cancelled." % message_bit)

    make_status_feedback_due.short_description = "Mark selected Interview's status as Cancelled"
