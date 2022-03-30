from consultant.models import *
from django.contrib import admin
from import_export.admin import ExportActionModelAdmin


@admin.register(Consultant)
class ConsultantAdmin(ExportActionModelAdmin):
    fieldsets = (
        ('Personal info', {'fields': ('name', 'email', 'skills', 'links', 'domain', 'skype', 'ssn', 'current_city',
                                      'phone_no', 'gender', 'date_of_birth')}),
        ('Other details', {'fields': ('status', 'work_type')}),
        ('Login details', {'fields': ('first_login', 'is_active', 'remote_only')}),
        ('Petition', {'fields': ('p_is_active', 'visa_petition', 'pin')}),
    )

    actions = ["export_as_csv"]
    list_filter = ('status', 'work_type', 'remote_only', 'first_login')
    search_fields = ('id', 'email', 'name', 'skills', 'current_city', 'status')
    list_display = ('id', 'name', 'email', 'date_of_birth', 'domain', 'skills', 'status', 'current_city', 'ssn',
                    'links', 'gender', 'work_type', 'remote_only', 'password', 'is_active', 'first_login', 'pin')

    class Media(object):
        css = {'all': ('no-more-warnings.css',)}


@admin.register(ConsultantResetPasswordToken)
class ConsultantResetPasswordTokenAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'key', 'created_at', 'user_agent')
    search_fields = ('consultant__name', 'consultant__email', 'key')


@admin.register(ConsultantToken)
class ConsultantTokenAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'key', 'created')
    search_fields = ('consultant__name', 'consultant__email', 'key')


@admin.register(ConsultantPetitionToken)
class ConsultantPetitionTokenAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'key', 'created')
    search_fields = ('consultant__name', 'consultant__email', 'key')


@admin.register(ConsultantProfile)
class ConsultantProfileAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'title', 'consultant__name', 'consultant__email', 'profile_owner__employee_name')
    list_display = ('id', 'title', 'consultant', 'profile_owner', 'date_of_birth', 'linkedin', 'current_city',
                    'profile_owner', 'visa_type', 'visa_start', 'visa_end', 'links', 'education')


@admin.register(WorkAuth)
class WorkAuthAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('is_current', 'visa_type')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'visa_type')
    list_display = ('id', 'consultant', 'visa_type', 'visa_start', 'visa_end', 'is_current', 'created')


@admin.register(Education)
class EducationAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'org_name', 'title', 'major', 'city')
    list_display = ('id', 'title', 'consultant', 'org_name', 'edu_type', 'major', 'start_date', 'end_date', 'city')


@admin.register(Experience)
class ExperienceAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'title', 'city')
    list_display = ('id', 'title', 'consultant', 'exp_type', 'start_date', 'end_date', 'city')


@admin.register(ConsultantMarketing)
class ConsultantMarketingAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('status',)
    search_fields = ('id', 'consultant__name', 'consultant__email')
    list_display = ('id', 'consultant', 'start', 'end', 'in_pool', 'cycle', 'status', 'previous_marketing_days',)

    def team_display(self, obj):
        return ", ".join([
            team.name for team in obj.teams.all()
        ])

    team_display.short_description = "Teams"


@admin.register(ConsultantRateRevision)
class ConsultantRateRevisionAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email')
    list_display = ('id', 'consultant', 'rate', 'start', 'end', 'feedback')


@admin.register(PayrollEmployer)
class PayrollEmployerAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'consultant', 'name', 'start')
    search_fields = ('id', 'consultant__name', 'consultant__email')


@admin.register(ConsultantPOC)
class ConsultantPOCAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('poc_type',)
    list_display = ('id', 'consultant', 'poc_type', 'poc', 'start', 'end')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'poc__employee_name')


@admin.register(Feedback)
class FeedbackAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'consultant', 'feedback_type', 'rating', 'created')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'feedback_type', 'rating', 'created')


@admin.register(ConsultantExit)
class ConsultantExitAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'type', 'resign_date', 'last_date')
    list_display = ('id', 'consultant', 'type', 'resign_date', 'last_date', 'notice_period', 'legal_action',
                    'exit_details', 'reasons_display')

    def reasons_display(self, obj):
        return ", ".join([
            reasons.name for reasons in obj.reasons.all()
        ])

    reasons_display.short_description = "Reasons"


@admin.register(ExitReason)
class ExitReasonAdmin(ExportActionModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name')


@admin.register(MSAccount)
class MSAccountAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('licence_assigned',)
    search_fields = ('email', 'consultant__email', 'user_id', 'member_id')
    list_display = ('id', 'email', 'consultant', 'licence_assigned', 'user_id', 'member_id')
