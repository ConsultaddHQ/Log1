from django.contrib import admin
from import_export.admin import ExportActionModelAdmin

from .models import Consultant, ConsultantProfile, ConsultantMarketing, ConsultantRateRevision, ConsultantPOC, \
    Education, Experience, WorkAuth, ConsultantToken, ConsultantPetitionToken, Terminate, Feedback


@admin.register(Consultant)
class ConsultantAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('status', 'work_type', 'remote_only', 'first_login')
    search_fields = ('id', 'email', 'name', 'skills', 'current_city', 'status')
    list_display = ('id', 'name', 'email', 'date_of_birth', 'domain', 'skills', 'status', 'current_city', 'ssn',
                    'links', 'gender', 'work_type', 'remote_only', 'password', 'is_active', 'first_login', 'pin')

    class Media(object):
        css = {'all': ('no-more-warnings.css',)}


@admin.register(ConsultantToken)
class ConsultantTokenAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'key', 'created')


@admin.register(ConsultantPetitionToken)
class ConsultantPetitionTokenAdmin(admin.ModelAdmin):
    list_display = ('consultant', 'key', 'created')


@admin.register(ConsultantProfile)
class ConsultantProfileAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'profile_owner__employee_name')
    list_display = ('id', 'title', 'consultant', 'profile_owner', 'date_of_birth', 'linkedin', 'current_city',
                    'profile_owner', 'visa_type', 'visa_start', 'visa_end', 'links', 'education')


@admin.register(WorkAuth)
class WorkAuthAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_filter = ('is_current', 'visa_type')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'visa_type')
    list_display = ('id', 'consultant', 'visa_type', 'visa_start', 'visa_end', 'is_current')


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
    list_display = ('id', 'cycle', 'consultant', 'start', 'end', 'in_pool', 'preferred_location', 'team_display',
                    'status', 'primary_marketer', 'previous_marketing_days')

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


@admin.register(ConsultantPOC)
class ConsultantPOCAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    list_display = ('id', 'consultant', 'poc_type', 'poc', 'start', 'end')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'poc__employee_name')


@admin.register(Feedback)
class FeedbackAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'feedback_type', 'rating', 'created')
    list_display = ('id', 'consultant', 'feedback_type', 'rating', 'created')


@admin.register(Terminate)
class TerminateAdmin(ExportActionModelAdmin):
    actions = ["export_as_csv"]
    search_fields = ('id', 'consultant__name', 'consultant__email', 'reason', 'resign_date', 'last_date')
    list_display = ('id', 'consultant', 'reason', 'resign_date', 'last_date', 'notice_period', 'exit_details')
