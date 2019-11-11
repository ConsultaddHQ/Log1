from django.contrib import admin

from utils_app.admin import ExportCsvMixin
from .models import Consultant, ConsultantProfile, ConsultantMarketing, ConsultantRateRevision, FeedbackDetail, \
    ConsultantPOC, ConsultantFeedback, Education, Experience, WorkAuth


@admin.register(Consultant)
class ConsultantAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'name', 'email', 'date_of_birth', 'phone_no', 'skills', 'status', 'current_city', 'ssn',
                    'links', 'gender', 'work_type')
    search_fields = ('id', 'email', 'name', 'skills', 'current_city', 'status')
    actions = ["export_as_csv"]


@admin.register(ConsultantProfile)
class ConsultantProfileAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'title', 'consultant', 'profile_owner', 'date_of_birth', 'linkedin', 'current_city',
                    'profile_owner', 'visa_type', 'visa_start', 'visa_end', 'links', 'education')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'profile_owner__employee_name')
    actions = ["export_as_csv"]


@admin.register(WorkAuth)
class WorkAuthAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'consultant', 'visa_type', 'visa_start', 'visa_end', 'is_current')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'visa_type')
    actions = ["export_as_csv"]


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'title', 'consultant', 'org_name', 'edu_type', 'major', 'start_date', 'end_date', 'city')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'org_name', 'title', 'major', 'city')
    actions = ["export_as_csv"]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'title', 'consultant', 'exp_type', 'start_date', 'end_date', 'city')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'title', 'city')
    actions = ["export_as_csv"]


@admin.register(FeedbackDetail)
class FeedbackDetail(admin.ModelAdmin):
    list_display = ('id', 'role', 'experience', 'programming', 'communication', 'problem_solving', 'organizational')
    search_fields = ('id',)


@admin.register(ConsultantMarketing)
class ConsultantMarketingAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'cycle', 'consultant', 'start', 'end', 'in_pool', 'preferred_location', 'team_display',
                    'primary_marketer', 'marketer_display')
    search_fields = ('id', 'consultant__employee_name', 'consultant__email')
    actions = ["export_as_csv"]

    def team_display(self, obj):
        return ", ".join([
            team.name for team in obj.teams.all()
        ])

    team_display.short_description = "Teams"

    def marketer_display(self, obj):
        return ", ".join([
            marketer.employee_name for marketer in obj.marketer.all()
        ])

    marketer_display.short_description = "Marketers"


@admin.register(ConsultantRateRevision)
class ConsultantRateRevisionAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'consultant', 'rate', 'start', 'end', 'feedback')
    search_fields = ('id', 'consultant__name', 'consultant__email')
    actions = ["export_as_csv"]


@admin.register(ConsultantPOC)
class ConsultantPOCAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'consultant', 'poc_type', 'poc', 'start', 'end')
    search_fields = ('id', 'consultant__name', 'consultant__email', 'poc__employee_name')
    actions = ["export_as_csv"]


@admin.register(ConsultantFeedback)
class ConsultantFeedbackAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('id', 'consultant', 'rating', 'feedback_type', 'role', 'experience', 'programming', 'communication',
                    'problem_solving', 'organizational')
    search_fields = ('id', 'consultant__name', 'feedback_type')
    actions = ["export_as_csv"]

    def role(self, obj):
        return obj.feedback.role

    role.short_description = "Role"

    def experience(self, obj):
        return obj.feedback.experience

    experience.short_description = "Experience"

    def programming(self, obj):
        return obj.feedback.programming

    programming.short_description = "Programming"

    def communication(self, obj):
        return obj.feedback.communication

    communication.short_description = "Communication"

    def problem_solving(self, obj):
        return obj.feedback.problem_solving

    problem_solving.short_description = "Problem Solving"

    def organizational(self, obj):
        return obj.feedback.organizational

    organizational.short_description = "Organizational"
