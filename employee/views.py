import logging
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models.functions import Lower
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, exceptions, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from employee.serializers import *
from employee.models import Role, Team
from utils_app.mailing import send_email
from activity.views import create_activity
from employee.models import ResetPasswordToken, clear_expired, get_password_reset_token_expiry_time, Asset

logger = logging.getLogger(__name__)


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
            employee_id = int(request.data.get('employee_id'))
            role = request.data.get('role')
            email = request.data.get('email')
            name = request.data.get('name')
            phone = request.data.get('phone')
            gender = request.data.get('gender').lower()
            password = request.data.get('password').strip()
            team = Team.objects.get(name=request.data.get('team'))

            user = User.objects.filter(employee_id__exact=employee_id)
            if user:
                logger.error("User already exist")
                return Response({
                    "result": "User already exist",
                    "data": self.serializer_class(user, many=True).data[0]},
                    status=status.HTTP_406_NOT_ACCEPTABLE)
            user = User.objects.create_user(employee_id, email, name, team, gender, phone, password)
            for i in role:
                r = Role.objects.get(name=i)
                user.role.add(r)
            return Response({"result": "success", "data": self.serializer_class(user).data}, status=201)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
        """
        employee_id = request.data.get('employee_id')
        if employee_id:
            user = get_object_or_404(User, employee_id=employee_id)
        else:
            return Response({"error": "Employee Id is Empty"}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(employee_id=user.employee_id, password=request.data.get('password').strip())
        if user:
            user.last_login = datetime.now()
            user.save()
            return Response({"result": self.login_serializer_class(user).data}, status=status.HTTP_202_ACCEPTED)
        logger.error("Incorrect Employee Id/Password")
        return Response({"error": "Incorrect Employee Id/Password"}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeViewSets(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs.get('pk'))
            serializer = self.serializer_class(user)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('query', '')
            user_type = request.query_params.get('type', None)
            if user_type:
                users = User.objects.filter(role__name=user_type)
            elif user_type == 'team':
                if 'superadmin' in request.user.roles:
                    users = User.objects.filter(role__name='marketer')
                else:
                    users = User.objects.filter(team=request.user.team, role__name='marketer')
            else:
                users = User.objects.filter(employee_name__icontains=query).exclude(role__name='consultant')
            users = users.annotate(name=Lower('employee_name')).order_by('name')
            data = users.values('id', 'employee_id', 'email', 'name')
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='role')
    def role(self, request):
        roles = Role.objects.all().values('id', 'name')
        return Response({"results": roles}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        teams = Team.objects.filter(dept='Marketing').values('id', 'name', 'dept')
        return Response({"results": teams}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        if request.user.check_password(current_password):
            request.user.set_password(new_password)
            request.user.save()
            return Response({"result": "password updated"}, status=status.HTTP_200_OK)
        return Response({"error": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['delete'], detail=False, url_path='logout')
    def logout(self, request, *args, **kwargs):
        """
            Logout for authenticated user
        """
        token = get_object_or_404(Token, key=request.auth)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        clear_expired(now_minus_expiry_time)

        users = User.objects.filter(email__iexact=email)

        active_user_found = False
        for user in users:
            if user.is_active and user.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            logger.info("User is not active")
            raise exceptions.ValidationError({
                'email': [_(
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
                    'to': [user.email],
                    'cc': [],
                    'bcc': [],
                    'subject': 'Reset Log1 Password',
                    'template': '../templates/password_reset.html',
                    'context': {
                        'employee_id': user.employee_id,
                        'name': user.employee_name,
                        'email': user.email,
                        'token': token,
                    },
                }
                res, error = user.send_mail(mail_data)
                if error == 'error':
                    logger.error(res)
                    return Response({'error': str(res)}, status=status.HTTP_200_OK)
        return Response({'status': 'OK'}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        serializer = self.pass_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({'status': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

        if timezone.now() > expiry_date:
            reset_password_token.delete()
            return Response({'status': 'expired'}, status=status.HTTP_404_NOT_FOUND)

        reset_password_token.user.set_password(password)
        reset_password_token.user.save()

        # Delete all password reset tokens for this user
        ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()

        return Response({'status': 'OK'}, status=status.HTTP_200_OK)


class AssetsViewSets(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    field_list = ['id', 'email', 'number', 'username', 'password', 'provider', 'modified', 'tech',
                  'created', 'alter_email', 'alter_number', 'remarks', 'asset_type', 'owner__employee_name']

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        try:
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            serializer = self.serializer_class(asset)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            assets_of = request.query_params.get('asset')
            if assets_of == 'shared':
                asset = Asset.objects.filter(shared_to=request.user, is_deleted=False)
            else:
                asset = Asset.objects.filter(owner=request.user, is_deleted=False)

            email_asset = asset.filter(asset_type='email')
            social_asset = asset.filter(asset_type='social')
            number_asset = asset.filter(asset_type='number')
            job_board_asset = asset.filter(asset_type='job_board')

            data = {
                "email_asset": email_asset.values(*self.field_list),
                "social_asset": social_asset.values(*self.field_list),
                "number_asset": number_asset.values(*self.field_list),
                "job_board_asset": job_board_asset.values(*self.field_list),
            }
            return Response({"results": data}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            asset = Asset.objects.create(
                username=data['username'],
                password=data['password'],
                email=data['email'],
                provider=data['username'],
                owner=request.user,
            )
            serializer = self.serializer_class(asset, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"error": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        try:
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            password = asset.password
            alter_num = asset.alter_number
            serializer = self.serializer_class(asset, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                pass_string, num_string = '', ''
                if asset.password != password:
                    pass_string = 'changed password from \"{}\" to \"{}\"'.format(password, asset.password)
                if asset.alter_number != alter_num:
                    num_string = 'changed Alternate number from \"{}\" to \"{}\"'.format(alter_num, asset.alter_number)
                if pass_string and num_string:
                    final_string = pass_string + " and " + num_string
                else:
                    if pass_string:
                        final_string = pass_string
                    elif num_string:
                        final_string = num_string
                    else:
                        final_string = "Nothing"
                desc = "{} updated {} of {} asset".format(request.user.employee_name.title(), final_string,
                                                          serializer.data['asset_type'])
                create_activity(asset.id, 'asset', request.user, desc, 'updated')
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        try:
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            asset.is_deleted = True
            asset.save()
            desc = "{} deleted {} asset".format(request.user.employee_name.title(), asset.asset_type)
            create_activity(asset.id, 'asset', request.user, desc, 'deleted')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='share')
    def share(self, request):
        assets = request.data.get('assets')
        users = request.data.get('users')
        try:
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
                desc = "{} shared {} asset to {}".format(request.user.employee_name.title(), asset.asset_type, user_list)
                create_activity(asset.id, 'asset', request.user, desc, 'updated')
            return Response({"result": "ok"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='un_share')
    def un_share(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        user_id = request.data.get('user')
        try:
            asset = get_object_or_404(Asset, id=asset_id, owner=request.user)
            user = User.objects.get(id=user_id)
            asset.shared_to.remove(user)
            desc = "{} Unshared {} from {} asset".format(request.user.employee_name, user.employee_name, asset.asset_type)
            create_activity(asset.id, 'asset', request.user, desc, 'updated')
            serializer = self.serializer_class(asset)
            return Response({"result": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"error": "File format not supported"}, status=status.HTTP_400_BAD_REQUEST)

            if 'Username' not in df.columns:
                return Response({"result": "Invalid Data Format"}, status=status.HTTP_404_NOT_FOUND)
            if not df.empty:
                created, updated, failed = 0, 0, 0
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
                            logger.error(row["Username"], request.user.employee_name, "Asset Type not found")
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
                        logger.error(row["Username"], request.user.employee_name, e)
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
                send_email(mail_data, "Log1")
                return Response({"result": "Upload Complete"}, status=status.HTTP_201_CREATED)
            return Response({"result": "Empty File"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            logger.error(error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
