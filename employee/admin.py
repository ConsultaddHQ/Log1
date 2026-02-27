from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionModelAdmin

from utils_app.admin import ExportCsvMixin
from employee.models import User, Role, Team, ResetPasswordToken, Asset, Tagging, Handover, DefaultCalendar, \
    Certificate, CertificateInfo

admin.site.site_header = "Log1"


@admin.register(User)
class CustomUserAdmin(UserAdmin, ExportCsvMixin):
    fieldsets = (
        (None, {'fields': ('team', 'employee_id', 'username', 'email', 'password')}),
        ('Personal info', {'fields': ('employee_name', 'avatar', 'phone', 'gender', 'role', 'technology', 'shift',
                                      'have_certificate', 'slack_id', 'associated_to')}),
        ('Permissions', {'fields': ('account_login', 'is_active', 'is_superuser', 'is_staff', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    actions = ["export_as_csv"]
    date_hierarchy = 'last_login'
    list_filter = ('team', 'role', 'is_active')
    search_fields = ('email', 'employee_id', 'employee_name', 'id', 'team__name')
    list_display = ('id', 'employee_id', 'email', 'employee_name', 'team', 'is_active', 'account_login', 'roles',
                    'slack_id', 'technology')

    def roles(self, obj):
        return ", ".join([
            role.name for role in obj.role.all()
        ])

    roles.short_description = "Roles"


class UserCreationFormExtended(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationFormExtended, self).__init__(*args, **kwargs)
        self.fields['employee_id'] = forms.IntegerField(label=_("Employee ID"))
        self.fields['username'] = forms.IntegerField(label=_("User Name"))
        self.fields['email'] = forms.EmailField(label=_("Email"), max_length=75)

    def clean_username(self):
        # Get the integer value of the username
        username = self.cleaned_data.get('username')

        # Convert the username to a string
        if username is not None:
            username = str(username)

        return username


UserAdmin.add_form = UserCreationFormExtended
UserAdmin.add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('employee_id', 'username', 'email', 'gender', 'password1', 'password2',)
    }),
)


@admin.register(Team)
class TeamAdmin(ExportActionModelAdmin):
    list_filter = ('dept',)
    search_fields = ('name', 'email')
    list_display = ('id', 'name', 'email', 'dept')


@admin.register(Role)
class RoleAdmin(ExportActionModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name', 'display_name')


@admin.register(ResetPasswordToken)
class ResetPasswordTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'ip_address', 'user_agent')
    search_fields = ('user__employee_name', 'user__email', 'key')


@admin.register(Asset)
class AssetAdmin(ExportActionModelAdmin):
    list_filter = ('asset_type', 'provider')
    list_display = ('id', 'owner', 'email', 'asset_type', 'provider')
    search_fields = ('id', 'owner__employee_name', 'email', 'asset_type', 'number')


@admin.register(Tagging)
class AssetAdmin(ExportActionModelAdmin):
    list_display = ('id', 'content_type', 'object_id')


@admin.register(Handover)
class HandoverAdmin(admin.ModelAdmin):
    search_fields = ('user__employee_name', 'user__employee_id', 'user__email', 'handover_to__employee_name')
    list_display = ('id', 'user', 'handover_to', 'created', 'modified')


@admin.register(DefaultCalendar)
class DefaultCalendarAdmin(admin.ModelAdmin):
    search_fields = ('user__employee_name', )
    list_display = ('id', 'user', 'emails')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    search_fields = ('name', )
    list_display = ('id', 'name', 'issued_by')


@admin.register(CertificateInfo)
class CertificateInfoAdmin(admin.ModelAdmin):
    search_fields = ('employee__employee_name', 'certificate__name')
    list_display = ('id', 'employee', 'certificate', 'issued_date', 'expiry_date', 'has_expiry')
