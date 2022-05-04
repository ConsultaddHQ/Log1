from itertools import chain
from datetime import timedelta, datetime

from django.utils import timezone
from django.db.models.functions import Lower
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Value, CharField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from rest_framework.mixins import *
from rest_framework.decorators import action
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from consultant.models import Consultant
from utils_app.mailing import send_email
from notification.models import FCMDevice
from api_key.permissions import HasAPIKey
from activity.views import create_activity
from log1.utils import write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG, get_page_limits
from employee.models import User, Role, Team, Asset, ResetPasswordToken, Handover, clear_expired, get_token_expiry_time
from employee.serializers import UserSerializer, UserSerializerLogin, EmailSerializer, PasswordTokenSerializer, \
    AssetSerializer, UserDirectorySerializer, HandoverSerializer


# Route - /auth/
class EmployeeAuthViewSets(GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    login_serializer_class = UserSerializerLogin

    @action(methods=['post'], detail=False, url_path='register')
    def register(self, request):
        """
            User Register
            :param request, email, password, employee_id, name, phone, gender, team, role
        """
        try:
            role = request.data.get('role')
            name = request.data.get('name')
            email = request.data.get('email')
            phone = request.data.get('phone')
            gender = request.data.get('gender').lower()
            password = request.data.get('password').strip()
            employee_id = int(request.data.get('employee_id'))
            team = Team.objects.get(name=request.data.get('team'))

            user = User.objects.filter(employee_id__exact=employee_id)
            if user:
                return Response({"message": "User already exist",
                                 "data": self.serializer_class(user, many=True).data[0]['email']}, status=406)
            user = User.objects.create_user(
                employee_id, email, name, team, gender, phone, password
            )
            for i in role:
                r = Role.objects.get(name=i)
                user.role.add(r)
            return Response({"message": "Success", "data": self.serializer_class(user).data}, status=201)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
        """
        try:
            employee_id = request.data.get('employee_id', None)
            if not employee_id.isnumeric():
                return Response({"message": "Enter valid Employee Id"}, status=400)

            if employee_id:
                queryset = User.objects.filter(employee_id=employee_id)
                if not queryset:
                    return Response({"message": "This user not found"}, status=400)
            else:
                return Response({"message": "Employee Id is Empty"}, status=400)

            user = queryset.first()
            user = authenticate(employee_id=user.employee_id, password=request.data.get('password').strip())
            if user:
                if not user.account_login:
                    return Response({"message": "Your account is not active"}, status=400)
                user.last_login = datetime.now()
                user.save()
                fcm_token = request.data.get("fcm_token", None)
                if fcm_token:
                    fcm_token, created = FCMDevice.objects.get_or_create(
                        device_id=request.data.get("fcm_token"),
                        content_type=ContentType.objects.get(model='user')
                    )
                    fcm_token.type = 'web'
                    fcm_token.name = 'windows'
                    fcm_token.object_id = user.id
                    fcm_token.save()

                return Response({"data": self.login_serializer_class(user).data}, status=202)
            return Response({"message": "Incorrect Password", "error": "Incorrect Password"}, status=400)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": "Unable to Login", "error": str(error)}, status=400)


# Route - /employee/
class EmployeeViewSets(GenericViewSet, ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs.get('pk'))
            serializer = self.serializer_class(user)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', '')
            teams = request.GET.get('teams', None)
            user_type = request.GET.get('type', None)
            users = User.objects.exclude(role__name='consultant').exclude(account_login=False)
            if user_type:
                users = users.filter(role__name__iexact=user_type)
            elif teams:
                teams = teams.split(",")
                if 'Consultadd' in teams and 'superadmin' in request.user.roles:
                    users = users.filter(role__name='marketer')
                else:
                    users = users.filter(team__name__in=teams)
            elif user_type == 'team':
                if 'superadmin' in request.user.roles:
                    users = users.filter(role__name='marketer')
                else:
                    users = users.filter(team=request.user.team, role__name='marketer')

            users = users.filter(employee_name__istartswith=query)
            users = users.annotate(name=F('employee_name')).order_by(Lower('name'))
            data = users.values('id', 'employee_id', 'email', 'name')
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            role = request.data.get('role')
            name = request.data.get('name')
            email = request.data.get('email')
            phone = request.data.get('phone')
            gender = request.data.get('gender').lower()
            password = request.data.get('password').strip()
            employee_id = int(request.data.get('employee_id'))
            team = Team.objects.get(name=request.data.get('team'))

            user = User.objects.filter(employee_id__exact=employee_id)
            if user:
                return Response({"message": "User already exist",
                                 "data": self.serializer_class(user, many=True).data[0]['email']}, status=406)
            user = User.objects.create_user(
                employee_id, email, name, team, gender, phone, password
            )
            for i in role:
                r = Role.objects.get(id=i)
                user.role.add(r)
            return Response({"message": "Success", "data": self.serializer_class(user).data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=False, url_path='technology')
    def technology(self, request):
        try:
            technology = request.data.get('technology')
            if technology:
                request.user.technology = technology
                request.user.save()
                return Response({"message": "Technologies Updated"}, status=202)
            return Response({"message": "Input is empty"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='bulk_register')
    def bulk_register(self, request, *args, **kwargs):
        try:
            import pandas as pd
            file = request.FILES.get('file')
            file_extension = file.name.split(".")[-1]
            if file_extension == 'csv':
                df = pd.read_csv(file, encoding="ISO-8859-1", skip_blank_lines=False)
            elif file_extension == 'xlsx':
                df = pd.read_excel(file)
            else:
                return Response({"message": "File format not supported"}, status=400)

            created, failed, already = 0, 0, 0
            error = ""
            for index, row in df.iterrows():
                if pd.isnull(row["employee_id"]):
                    break
                try:
                    user = User.objects.filter(employee_id__exact=row["employee_id"])
                    if user:
                        already += 1
                    else:
                        team = Team.objects.get(name=row['team'])
                        user = User.objects.create_user(
                            team=team,
                            email=row["email"],
                            phone=row['phone'],
                            gender=row['gender'],
                            employee_name=row["name"],
                            username=int(row["employee_id"]),
                            employee_id=int(row["employee_id"]),
                        )
                        user.set_password(row['password'])
                        user.save()
                        role = Role.objects.get(name=row['role'])
                        user.role.add(role)
                        created += 1
                except Exception as e:
                    failed += 1
                    error += f"{row} \n"
                    write_exception(f"{row['employee_id']}, {e}", request)
                    continue
            data = {
                "error": error,
                "Failed": failed,
                "Created": created,
                "Already Exist": already,
            }
            return Response({"message": "Success", "data": data}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=False, url_path='profile')
    def profile(self, request):
        try:
            user_id = request.data.get('user_id')
            role_ids = request.data.get('role_id', [])
            team_id = request.data.get('team_id', None)
            if request.user.is_superuser:
                user = get_object_or_404(User, id=user_id)
                desc = ""
                if team_id:
                    prev_team = user.team.name
                    team = get_object_or_404(Team, id=team_id)
                    user.team = team
                    desc += f"{request.user.employee_name} changed team from {prev_team} to {team.name} "

                if role_ids:
                    role_names = []
                    user.role.clear()
                    for role_id in role_ids:
                        role = get_object_or_404(Role, id=role_id)
                        user.role.add(role)
                        role_names.append(role.name)
                    if team_id:
                        desc += f"and changed role to {', '.join(role_names)}"
                    else:
                        desc += f"{request.user.employee_name} changed role to {', '.join(role_names)}"

                user.save()
                if len(desc) > 0:
                    create_activity(user.id, 'user', request.user, desc, 'updated')
                return Response({"message": f"{user.employee_name}'s Profile updated"}, status=202)
            return Response({"message": DONT_HAVE_ACCESS}, status=401)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=False, url_path='account')
    def account(self, request):
        try:
            user_id = request.data.get('user_id')
            account_login = request.data.get('active', None)
            if request.user.is_superuser:
                user = get_object_or_404(User, id=user_id)
                if account_login is not None:
                    user.account_login = account_login
                    user.save()
                else:
                    return Response({"message": "Parameter is not correct", "error": str(account_login)}, status=400)

            if account_login:
                message = "Activated"
            else:
                message = "Deactivated"
            return Response({"message": f"Account {message}"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='me')
    def me(self, request):
        try:
            return Response({"data": UserSerializer(request.user).data}, status=200)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='role')
    def role(self, request):
        try:
            roles = Role.objects.all().values('id', 'name')
            return Response({"data": roles}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            query = request.GET.get('query', None)
            if query == 'all':
                teams = Team.objects.exclude(dept='marketing').values('id', 'name')
            else:
                teams = Team.objects.filter(dept='Marketing').values('id', 'name')
            return Response({"data": teams}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='logout')
    def logout(self, request):
        """
            Logout for authenticated user
        """
        token = get_object_or_404(Token, key=request.auth)
        token.delete()
        fcm_token = FCMDevice.objects.filter(object_id=token.user.id, content_type__model='user')
        if fcm_token:
            fcm_token.delete()
        return Response(status=204)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        try:
            current_password = request.data.get('cur_password')
            new_password = request.data.get('new_password')
            if request.user.check_password(current_password):
                request.user.set_password(new_password)
                request.user.save()
                return Response({"message": "password updated"}, status=200)
            return Response({"message": "Wrong Password"}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['get'], detail=False, url_path='directory')
    def directory(self, request):
        first, last = get_page_limits(request)
        try:
            if 'superadmin' in request.user.roles:
                query = request.GET.get('query', None)
                users = User.objects.all().exclude(role__name='consultant')
                if query:
                    query = query.lstrip().replace(':amp:', '&')
                    users = users.filter(
                        Q(employee_name__icontains=query) |
                        Q(email__iexact=query)
                    )
                total = users.count()
                serializer = UserDirectorySerializer(users[first:last], many=True)
                return Response({"data": serializer.data, "total": total}, status=200)
            return Response({"message": DONT_HAVE_ACCESS}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /password/
class ResetPasswordViewSets(GenericViewSet):
    queryset = User.objects.all()
    permission_classes = ()
    authentication_classes = ()
    serializer_class = EmailSerializer
    pass_serializer_class = PasswordTokenSerializer

    @action(methods=['post'], detail=False, url_path='token_request')
    def token_request(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        password_reset_token_validation_time = get_token_expiry_time()

        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        clear_expired(now_minus_expiry_time)

        users = User.objects.filter(email__iexact=email)

        active_user_found = False
        for user in users:
            if user.is_active and user.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            raise exceptions.ValidationError({
                'message': [_(
                    "There is no active user associated with this e-mail address or the password can not be changed")],
            })
        ip = request.META['REMOTE_ADDR']
        for user in users:
            if user.is_active and user.has_usable_password():
                if user.password_reset_tokens.all().count() > 0:
                    token = user.password_reset_tokens.all()[0]
                else:
                    token = ResetPasswordToken.objects.create(
                        user=user,
                        user_agent=request.META['HTTP_USER_AGENT'],
                        ip_address=ip if ip else '127.0.0.1'
                    )
                mail_data = {
                    'subject': 'Reset Log1 Password',
                    'to': [user.email], 'cc': [], 'bcc': [],
                    'template': '../templates/password_reset.html',
                    'context': {
                        'employee_id': user.employee_id,
                        'name': user.employee_name,
                        'email': user.email,
                        'token': token.key,
                    },
                }
                res, error = user.send_mail(mail_data)
                if error == "ok":
                    return Response({"message": f"Mail sent on {user.email}", "data": res}, status=200)
                else:
                    write_info(message=res, function='token_request')
                    return Response({"message": "Something went wrong", "error": str(res)}, status=400)
            else:
                return Response({"message": "User is not active"}, status=400)
        return Response({"message": "Something went wrong"}, status=400)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        try:
            serializer = self.pass_serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            password = serializer.validated_data['password']
            token = serializer.validated_data['token']

            password_reset_token_validation_time = get_token_expiry_time()

            reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

            if reset_password_token is None:
                return Response({'message': 'Token not found'}, status=404)

            expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

            if timezone.now() > expiry_date:
                reset_password_token.delete()
                return Response({'message': 'Token Expired'}, status=404)

            reset_password_token.user.set_password(password)
            reset_password_token.user.save()

            # Delete all password reset tokens for this user
            ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()

            return Response({'message': 'Password changed successfully'}, status=200)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /assets/
class AssetsViewSets(ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    field_list = ['id', 'email', 'number', 'username', 'password', 'provider', 'modified', 'tech',
                  'created', 'alter_email', 'alter_number', 'remarks', 'asset_type', 'owner__employee_name']

    def retrieve(self, request, *args, **kwargs):
        try:
            asset = get_object_or_404(Asset, id=kwargs.get('pk'), owner=request.user)
            serializer = self.serializer_class(asset)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            assets_of = request.GET.get('asset')
            if assets_of == 'shared':
                asset = Asset.objects.filter(shared_to=request.user, is_deleted=False)
            else:
                asset = Asset.objects.filter(owner=request.user, is_deleted=False)

            email_asset = asset.filter(asset_type='email')
            social_asset = asset.filter(asset_type='social')
            number_asset = asset.filter(asset_type='number').exclude(provider='twilio')
            job_board_asset = asset.filter(asset_type='job_board')

            data = {
                "email_asset": email_asset.values(*self.field_list),
                "social_asset": social_asset.values(*self.field_list),
                "number_asset": number_asset.values(*self.field_list),
                "job_board_asset": job_board_asset.values(*self.field_list),
            }
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            asset = Asset.objects.create(
                owner=request.user,
                email=data['email'],
                username=data['username'],
                password=data['password'],
                provider=data['username'],
            )
            serializer = self.serializer_class(asset, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data, "message": "Asset added"}, status=201)
            return Response({"message": str(serializer.errors)}, status=400)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            asset = get_object_or_404(Asset, id=kwargs.get('pk'), owner=request.user)
            password = asset.password
            alter_num = asset.alter_number
            serializer = self.serializer_class(asset, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                pass_string, num_string = '', ''
                if asset.password != password:
                    pass_string = f'changed password from \"{password}\" to \"{asset.password}\"'
                if asset.alter_number != alter_num:
                    num_string = f'changed Alternate number from \"{alter_num}\" to \"{asset.alter_number}\"'
                if pass_string and num_string:
                    final_string = pass_string + " and " + num_string
                else:
                    if pass_string:
                        final_string = pass_string
                    elif num_string:
                        final_string = num_string
                    else:
                        final_string = "Nothing"
                desc = f"{request.user.employee_name.title()} updated {final_string} of " \
                       f"{serializer.data['asset_type']} asset"
                create_activity(asset.id, 'asset', request.user, desc, 'updated')
            return Response({"data": serializer.data, "message": "Asset updated"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            asset = get_object_or_404(Asset, id=kwargs.get('pk'), owner=request.user)
            asset.is_deleted = True
            asset.save()
            desc = f"{request.user.employee_name.title()} deleted {asset.asset_type} asset"
            create_activity(asset.id, 'asset', request.user, desc, 'deleted')
            return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)

    @action(methods=['put'], detail=False, url_path='share')
    def share(self, request):
        users = request.data.get('users', [])
        assets = request.data.get('assets', [])
        try:
            if len(assets) < 1:
                return Response({"message": "Please select Asset"}, status=404)

            for asset_id in assets:
                asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
                names = []
                for u in users:
                    if u == request.user.id:
                        continue
                    user = User.objects.get(id=u)
                    names.append(user.employee_name)
                    asset.shared_to.add(user)
                user_list = ", ".join(names[:len(names) - 1]) + " and " + names[-1] if len(names) > 1 else "".join(
                    names)
                desc = f"{request.user.employee_name.title()} shared {asset.asset_type} asset to {user_list}"
                create_activity(asset.id, 'asset', request.user, desc, 'updated')
            return Response({"message": "Asset shared"}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['put'], detail=True, url_path='un_share')
    def un_share(self, request, pk):
        try:
            asset = get_object_or_404(Asset, id=pk, owner=request.user)
            user = User.objects.get(id=request.data.get('user'))
            asset.shared_to.remove(user)
            desc = f"{request.user.employee_name} Unshared {user.employee_name} from {asset.asset_type} asset"
            create_activity(asset.id, 'asset', request.user, desc, 'updated')
            serializer = self.serializer_class(asset)
            return Response({"data": serializer.data}, status=202)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='bulk_upload')
    def bulk_upload(self, request):
        try:
            import pandas as pd
            file = request.FILES.get('file')
            file_extension = file.name.split(".")[-1]
            if file_extension == 'csv':
                df = pd.read_csv(file, encoding="ISO-8859-1", skip_blank_lines=False)
            elif file_extension == 'xlsx':
                df = pd.read_excel(file)
            else:
                return Response({"message": "File format not supported"}, status=400)
            if not df.empty:
                created, updated, failed = 0, 0, 0
                if not {'Username', 'Provider', 'Password', 'Asset Type', 'Email', 'Technology',
                        'Remarks', 'Phone Number', 'Alternate Email', 'Alternate Number'
                        }.issubset(set(df.columns)):
                    return Response({"message": "Invalid Data Format"}, status=404)

                for index, row in df.iterrows():
                    if pd.isnull(row["Username"]):
                        break
                    try:
                        if not pd.isnull(row['Asset Type']):
                            asset, new_asset = Asset.objects.get_or_create(
                                owner=request.user,
                                provider=row['Provider'],
                                username=row['Username'],
                                password=row['Password'],
                                asset_type=row['Asset Type'].lower()
                            )
                        else:
                            write_exception(f"{row['Username']} {request.user.employee_name} Asset Type not found")
                            failed += 1
                            continue
                        asset.email = row['Email'] if not pd.isnull(row['Email']) else ""
                        asset.tech = row['Technology'] if not pd.isnull(row['Technology']) else ""
                        asset.remarks = row['Remarks'] if not pd.isnull(row['Remarks']) else ""
                        asset.number = row['Phone Number'] if not pd.isnull(row['Phone Number']) else ""
                        asset.asset_type = row['Asset Type'] if not pd.isnull(row['Asset Type']) else ""
                        asset.alter_email = row['Alternate Email'] if not pd.isnull(row['Alternate Email']) else ""
                        asset.alter_number = row['Alternate Number'] if not pd.isnull(
                            row['Alternate Number']) else ""
                        asset.save()

                        if new_asset:
                            created += 1
                        else:
                            updated += 1

                    except Exception as e:
                        write_exception(f"{row['Username']} {request.user.employee_name} {e}", request)
                        failed += 1
                        continue
                mail_data = {
                    'to': [request.user.email],
                    'bcc': [],
                    'cc': [],
                    'subject': 'Log1 bulk upload of Asset information',
                    'template': '../templates/asset_report.html',
                    'context': {
                        'user': request.user.employee_name,
                        'created': created,
                        'updated': updated,
                        'failed': failed,
                    },
                }
                send_email(mail_data, "log1@consultadd.com", request=request)
                return Response({"message": "Upload Complete", "count": mail_data['context']}, status=201)
            return Response({"message": "Empty File"}, status=404)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /users/
class AllUsersViewSet(GenericViewSet, ListModelMixin):
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', '').lstrip().replace(':amp:', '&')
            users = self.queryset.filter(employee_name__istartswith=query, is_active=True).annotate(
                name=F('employee_name'),
                type=Value('user', CharField())
            ).values('id', 'name', 'type')

            consultants = Consultant.objects.filter(name__istartswith=query).exclude(status='terminated').annotate(
                type=Value('consultant', CharField())
            ).values('id', 'name', 'type')

            result_list = list(chain(consultants[:5], users[:5]))
            return Response({"data": result_list}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)


# Route - /handover/
class HandoverViewSets(GenericViewSet, CreateModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = Handover.objects.all()
    serializer_class = HandoverSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            if 'superadmin' in request.user.roles:
                user = get_object_or_404(User, id=request.data.get('user_id'))
                handover_to = get_object_or_404(User, id=request.data.get('handover_to_id'))
                handover, created = Handover.objects.get_or_create(user=user)
                handover_to_name = handover_to.employee_name
                handover.handover_to = handover_to
                handover.save()
                desc = f"{request.user.employee_name} handed-over {user.employee_name} to {handover_to_name}"
                create_activity(user.id, 'user', request.user, desc, 'created')
                return Response({"message": f"User handed over to {handover_to_name}"}, status=201)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    def update(self, request, *args, **kwargs):
        try:
            if 'superadmin' in request.user.roles:
                user_id = kwargs.get('pk', None)
                user = get_object_or_404(User, id=user_id)
                handover_to = get_object_or_404(User, id=request.data.get('handover_to_id'))
                qs = Handover.objects.filter(user_id=user_id)
                if qs:
                    handover = qs.first()
                    prev_handover = handover.handover_to.employee_name
                    handover_to_name = handover_to.employee_name
                    handover.handover_to = handover_to
                    handover.save()
                    desc = f"{request.user.employee_name} changed handover of {user.employee_name} from " \
                           f"{prev_handover}  to {handover_to_name}"
                    create_activity(user.id, 'user', request.user, desc, 'update')
                    return Response({"message": f"User handed over to {handover_to_name}"}, status=202)
                else:
                    return Response({"message": "Handover not found"}, status=404)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            if 'superadmin' in request.user.roles:
                user_id = kwargs.get('pk', None)
                if not user_id:
                    return Response({"message": f"User is not provided"}, status=400)
                user = get_object_or_404(User, id=user_id)
                handovers = Handover.objects.filter(user_id=user_id)
                if handovers:
                    desc = f"{request.user.employee_name} removed handover of {user.employee_name}"
                    create_activity(user.id, 'user', request.user, desc, 'update')
                    handovers.delete()
                    return Response({"message": f"User handover removed"}, status=202)
                else:
                    return Response({"message": "Handover not found"}, status=404)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=405)


# Route - /login/
class LoginViewSet(GenericViewSet, CreateModelMixin):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    authentication_classes = (HasAPIKey,)

    def create(self, request, *args, **kwargs):
        result = {}
        try:

            data = {
                "role": request.data.get('role'),
                "name": request.data.get('name'),
                "team": request.data.get('team'),
                "email": request.data.get('email'),
                "phone": request.data.get('phone', None),
                "gender": request.data.get('gender').lower(),
                "password": request.data.get('password').strip(),
                "employee_id": int(request.data.get('employee_id')),
                "roles": request.data.get('roles', [])
            }

            # Log1 login

            user = User.objects.create_user(**data)

            result["Log1"] = f'{user.id} Created'
            return Response({"message": result}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": result, "error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='bulk_create')
    def create_bulk(self, request, *args, **kwargs):
        result = {}
        try:

            records = request.data.get('data')
            roles = [record.get('roles', []) for record in records]
            users = [User(
                team=record.get('team'),
                email=record.get('email'),
                phone=record.get('phone'),
                gender=record.get('gender'),
                employee_name=record.get('name'),
                username=int(record.get('employee_id')),
                employee_id=int(record.get('employee_id')),
            ) for record in records]
            for user, role in zip(users, roles):
                for role_name in role:
                    role_object = Role.objects.get(name=role_name)
                    user.role.add(role_object)

            users = User.objects.bulk_create(users)
            users = [user.employee_id for user in users]
            result["response"] = f"{len(users)} users  Created"
            result["users"] = users

            return Response({"message": result}, status=201)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": result, "error": str(error)}, status=400)
