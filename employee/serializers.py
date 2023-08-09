from constance import config
from django.db.models import F
from rest_framework import serializers
from rest_framework.authtoken.models import Token

# from utils_app.calendar import get_profile_picture
from employee.models import User, Asset, Team, Role, Tagging, Handover, CertificateInfo


class UserSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'team', 'roles', 'gender', 'phone', 'avatar',
                  'is_superuser', 'technology')

    @staticmethod
    def get_team(obj):
        if obj.team:
            return obj.team.name
        return None

    # @staticmethod
    # def get_avatar(obj):
    #     return get_profile_picture(obj)


class UserDashboardSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    handover = serializers.SerializerMethodField()
    display_roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'avatar', 'team', 'gender', 'phone', 'roles', 'shift',
                  'is_superuser', 'technology', 'handover', 'project', 'display_roles', 'version', 'have_certificate')

    @staticmethod
    def get_team(obj):
        team = obj.team
        if team:
            return {
                "name": team.name,
                "department": team.dept
            }
        return None

    @staticmethod
    def get_avatar(obj):
        if obj.avatar:
            return obj.avatar.url

    @staticmethod
    def get_version(obj):
        return config.VERSION

    @staticmethod
    def get_roles(obj):
        if obj.role.all():
            return obj.role.all().values_list('name', flat=True)

    @staticmethod
    def get_display_roles(obj):
        if obj.role.all():
            return obj.role.all().values_list('display_name', flat=True)

    @staticmethod
    def get_handover(obj):
        if obj.handovers.all():
            return obj.handovers.all().values(name=F('user__employee_name'), employee_id=F('user__employee_id'))

    @staticmethod
    def get_project(obj):
        project = obj.projects.all()
        if project:
            current_project = project.filter(end=None, statuses__is_current=True, is_proxy_support=False,
                                             statuses__frequency__in=['active', 'less_active']).exclude(
                project__statuses__is_current=True, project__statuses__status__istartswith='terminated' or 'cancelled')
            data = [{
                "vendor": p.project.submission.lead.vendor_company.name
                if p.project.submission.lead.vendor_company.name else None,
                "employer": p.project.employer if p.project.employer else None,
                "id": p.project.id, "name": p.project.consultant.name, "client": p.project.submission.client,
            } for p in current_project]
            return {"current_project": data, "total": len(project)}
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'employee_name')


# Login
class UserSerializerLogin(UserSerializer):
    token = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'employee_name', 'email', 'token', 'team', 'roles', 'technology',
                  'shift', 'is_superuser')

    @staticmethod
    def get_token(obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    @staticmethod
    def get_team(obj):
        return obj.team.name


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'name', 'dept', 'scrum_timing')


class RoleSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ('id', 'name')

    @staticmethod
    def get_name(obj):
        return obj.display_name


class UserDirectorySerializer(serializers.ModelSerializer):
    team = TeamSerializer()
    role = RoleSerializer(many=True)
    handover_to = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'team', 'role', 'account_login', 'handover_to')

    @staticmethod
    def get_handover_to(obj):
        if obj.handover_to.exists():
            if obj.handover_to.first().handover_to:
                return UserDetailSerializer(obj.handover_to.first().handover_to).data
        return None


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordTokenSerializer(serializers.Serializer):
    password = serializers.CharField(style={'input_type': 'password'})
    token = serializers.CharField()


class AssetSerializer(serializers.ModelSerializer):
    shared_to = UserSerializer(many=True)
    owner_id = serializers.SerializerMethodField(read_only=True)
    owner_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Asset
        fields = ('id', 'email', 'number', 'username', 'password', 'owner_id', 'provider', 'modified', 'tech',
                  'created', 'alter_email', 'alter_number', 'remarks', 'asset_type', 'owner_name', 'shared_to')

    @staticmethod
    def get_owner_id(obj):
        return obj.owner.id

    @staticmethod
    def get_owner_name(obj):
        return obj.owner.employee_name


class TaggedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tagging
        fields = '__all__'


class HandoverUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'name', 'email')

    @staticmethod
    def get_name(obj):
        return obj.employee_name


class HandoverSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()

    class Meta:
        model = Handover
        fields = ('id', 'employee_id', 'name', 'email')

    @staticmethod
    def get_id(obj):
        return obj.user.id

    @staticmethod
    def get_email(obj):
        return obj.user.email

    @staticmethod
    def get_employee_id(obj):
        return obj.user.employee_id

    @staticmethod
    def get_name(obj):
        return obj.user.employee_name


class CertificateInfoSerializer(serializers.ModelSerializer):
    certificate = serializers.SerializerMethodField()

    class Meta:
        model = CertificateInfo
        fields = '__all__'

    @staticmethod
    def get_certificate(obj):
        return {
            "name": obj.certificate.name, "organization": obj.certificate.issued_by
        }

