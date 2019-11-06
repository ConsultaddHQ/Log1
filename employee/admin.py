from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from utils_app.admin import ExportCsvMixin
from api_key.admin import APIKeyModelAdmin
from .models import User, Role, Team, ResetPasswordToken, Asset, Organization, OrganizationAPIKey


@admin.register(User)
class CustomUserAdmin(UserAdmin, ExportCsvMixin):
    fieldsets = ((None, {'fields': ('team', 'employee_id', 'username', 'email', 'password')}),
                 ('Personal info', {'fields': ('employee_name', 'avatar', 'phone', 'gender', 'role')}),
                 ('Permissions', {'fields': ('is_active', 'is_superuser', 'is_staff', 'user_permissions')}),
                 ('Important dates', {'fields': ('last_login', 'date_joined')}),
                 )

    list_display = ('id', 'employee_id', 'email', 'employee_name', 'team', 'is_active', 'roles')
    search_fields = ('email', 'employee_id', 'employee_name', 'id', 'team__name')
    actions = ["export_as_csv"]

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
    list_display = ('id', 'name', 'email', 'address')
    search_fields = ('name', 'email')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(ResetPasswordToken)
class ResetPasswordTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'ip_address', 'user_agent')
    search_fields = ('user__employee_name', 'user__email', 'key')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'email', 'asset_type')
    search_fields = ('id', 'owner__employee_name', 'email', 'asset_type')


@admin.register(Organization)
class OrganizationModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    search_fields = ['name']


@admin.register(OrganizationAPIKey)
class OrganizationAPIKeyModelAdmin(APIKeyModelAdmin):
    list_display = [*APIKeyModelAdmin.list_display, "organization"]
    search_fields = [*APIKeyModelAdmin.search_fields, "organization__name"]

