from rest_framework import serializers
from rest_framework.authtoken.models import Token

from employee.models import User, Asset, Team, Tagging


class UserSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'avatar', 'team', 'roles', 'gender', 'phone')

    def get_team(self, obj):
        if obj.team:
            return obj.team.name
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'employee_name', 'avatar')


# Login
class UserSerializerLogin(UserSerializer):
    token = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'employee_id', 'employee_name', 'email', 'token', 'avatar', 'team', 'roles', 'is_superuser')

    def get_token(self, user):
        token, created = Token.objects.get_or_create(user=user)
        return token.key

    def get_team(self, obj):
        return obj.team.name


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'name', 'dept')


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

    def get_owner_id(self, obj):
        return obj.owner.id

    def get_owner_name(self, obj):
        return obj.owner.employee_name


class TaggedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tagging
        fields = '__all__'
