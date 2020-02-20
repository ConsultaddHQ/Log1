from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from utils_app.admin import ExportCsvMixin
from .models import User, Role, Team, ResetPasswordToken, Asset

admin.site.site_header = "Log1"


@admin.register(User)
class CustomUserAdmin(UserAdmin, ExportCsvMixin):
    fieldsets = ((None, {'fields': ('team', 'employee_id', 'username', 'email', 'password')}),
                 ('Personal info', {'fields': ('employee_name', 'avatar', 'phone', 'gender', 'role')}),
                 ('Permissions', {'fields': ('is_active', 'is_superuser', 'is_staff', 'user_permissions')}),
                 ('Important dates', {'fields': ('last_login', 'date_joined')}),
                 )

    actions = ["export_as_csv"]
    date_hierarchy = 'last_login'
    empty_value_display = '-------'
    list_filter = ('team', 'role', 'is_active')
    search_fields = ('email', 'employee_id', 'employee_name', 'id', 'team__name')
    list_display = ('id', 'employee_id', 'email', 'employee_name', 'team', 'is_active', 'roles')

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


UserAdmin.add_form = UserCreationFormExtended
UserAdmin.add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('employee_id', 'username', 'email', 'gender', 'password1', 'password2',)
    }),
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_filter = ('dept',)
    empty_value_display = '-------'
    search_fields = ('name', 'email')
    list_display = ('id', 'name', 'email', 'dept')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name')
    empty_value_display = '-------'


@admin.register(ResetPasswordToken)
class ResetPasswordTokenAdmin(admin.ModelAdmin):
    empty_value_display = '-------'
    list_filter = ('user__employee_name',)
    list_display = ('user', 'key', 'ip_address', 'user_agent')
    search_fields = ('user__employee_name', 'user__email', 'key')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    empty_value_display = '-------'
    list_filter = ('owner__employee_name', 'asset_type')
    list_display = ('id', 'owner', 'email', 'asset_type')
    search_fields = ('id', 'owner__employee_name', 'email', 'asset_type')
