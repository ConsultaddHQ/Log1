from rest_framework import serializers
from rest_framework.authtoken.models import Token

from utils_app.calendar import get_profile_picture
from employee.models import User, Asset, Team, Role, Tagging, Handover


class UserSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'avatar', 'team', 'roles', 'gender', 'phone',
                  'is_superuser', 'technology')

    @staticmethod
    def get_team(obj):
        if obj.team:
            return obj.team.name
        return None

    @staticmethod
    def get_avatar(obj):
        return get_profile_picture(obj)


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
        fields = ('id', 'employee_id', 'employee_name', 'email', 'token', 'avatar', 'team', 'roles', 'is_superuser')

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
        fields = ('id', 'name', 'dept')


class RoleSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ('id', 'name')

    @staticmethod
    def get_name(obj):
        return obj.name.title().replace("_", " ")


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
