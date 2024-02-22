import json
from itertools import chain
from datetime import timedelta, datetime

from dateutil import tz
from constance import config
from django.utils import timezone
from rest_framework.mixins import *
from rest_framework import exceptions
from django.contrib.auth import authenticate
from django.db.models.functions import Lower
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from django.db.models import Q, F, Value, CharField
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from api_key.models import APIKey
from .utils import valid_password
from activity.models import Activity
from consultant.models import Consultant
from notification.models import FCMDevice
from activity.views import create_activity
from utils_app.thred_mail import send_email
from tracking.models import Devices, Location
from utils_app.calendar import GoogleCalendar
from project.models import Project, ProjectSupport
from log1.utils import write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG, get_page_limits
from tracking.utils import get_address_by_location, generate_unique_cookies, string_to_decimal_point_converter
from employee.models import User, Role, Team, Asset, ResetPasswordToken, Handover, clear_expired, get_token_expiry_time, \
    DefaultCalendar, CertificateInfo, Certificate
from employee.serializers import UserSerializer, UserSerializerLogin, EmailSerializer, PasswordTokenSerializer, \
    AssetSerializer, UserDirectorySerializer, HandoverSerializer, UserDashboardSerializer, CertificateInfoSerializer


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
                                 "data": self.serializer_class(user, many=True).data[0]['email']},
                                status=status.HTTP_406_NOT_ACCEPTABLE)
            user = User.objects.create_user(
                employee_id, email, name, team, gender, phone, password
            )
            for i in role:
                r = Role.objects.get(name=i)
                user.role.add(r)
            return Response({"message": "Success", "data": self.serializer_class(user).data},
                            status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
        """
        try:
            employee_id = request.data.get('employee_id', None)
            latitude = request.data.get('latitude', None)
            longitude = request.data.get('longitude', None)

            if not employee_id.isnumeric():
                return Response({"message": "Enter valid Employee Id"}, status=status.HTTP_400_BAD_REQUEST)

            if employee_id:
                queryset = User.objects.filter(employee_id=employee_id)
                if not queryset:
                    return Response({"message": "This user not found"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Employee Id is Empty"}, status=status.HTTP_400_BAD_REQUEST)

            user = queryset.first()
            user = authenticate(employee_id=user.employee_id, password=request.data.get('password').strip())
            if user:
                # need to check if cookies id is available or not
                cookie_value = request.META.get('HTTP_X_ID_TOKEN', None)
                devices_cookies = Devices.objects.filter(cookies_value=cookie_value).first()
                other_device = Devices.objects.filter(user=user).last()

                if not devices_cookies:
                    device_id = other_device.device_id if other_device else 0
                    cookie_value = generate_unique_cookies()
                    devices_cookies = Devices.objects.create(
                        user=user,
                        device_id=device_id,
                        cookies_value=cookie_value,
                    )

                    # ip address and location needs to determine here
                    if latitude and longitude:
                        latitude = string_to_decimal_point_converter(latitude)
                        longitude = string_to_decimal_point_converter(longitude)
                        location_data = Location.objects.filter(latitude=latitude, longitude=longitude).first()
                        if location_data:
                            Location.objects.create(
                                latitude=latitude,
                                longitude=longitude,
                                place_name=location_data.place_name,
                                state=location_data.state,
                                country=location_data.country,
                                pin_code=location_data.pin_code,
                                display_name=location_data.display_name,
                                device=devices_cookies
                            )
                        else:
                            location_data = get_address_by_location(latitude, longitude)
                            if location_data:
                                Location.objects.create(
                                    device=devices_cookies,
                                    state=location_data["address"]["state"],
                                    place_name=location_data["address"]["town"] if 'town' in location_data[
                                        "address"] else location_data["address"]["city"],
                                    country=location_data["address"]["country"],
                                    pin_code=location_data["address"]["postcode"],
                                    display_name=location_data["display_name"]
                                )

                if not user.account_login:
                    return Response({"message": "Your account is not active"}, status=status.HTTP_400_BAD_REQUEST)
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

                return Response({
                    "data": self.login_serializer_class(user).data, "cookie": devices_cookies.cookies_value
                }, status=status.HTTP_202_ACCEPTED)
            return Response(
                {"message": "Incorrect Password", "error": "Incorrect Password"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as error:
            write_exception(message=error)
            return Response({"message": "Unable to Login", "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', '')
            teams = request.GET.get('teams', None)
            is_active = request.GET.get('is_active', None)
            user_type = request.GET.get('type', None)
            associate = json.loads(request.GET.get('associate', 'false'))
            users = User.objects.exclude(role__name='consultant')
            if is_active:
                users = users.filter(is_active=True, account_login=True)
            else:
                users = users.exclude(account_login=False)

            if user_type:
                users = users.filter(role__name__iexact=user_type)
            elif teams:
                teams = teams.split(",")
                if 'Consultadd' in teams and 'superadmin' in request.user.roles:
                    users = users.filter(role__name='marketer')
                elif associate:
                    users = users.filter(Q(team__name__in=teams) | Q(associated_to__name__in=teams))
                elif is_active:
                    users = users.filter(Q(team__name__in=teams) | Q(associated_to__name__in=teams))
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
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs.get('pk'))
            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = self.serializer_class(user)
            return Response({"result": serializer.data, "message": "User Updated"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                                 "data": self.serializer_class(user, many=True).data[0]['email']},
                                status=status.HTTP_406_NOT_ACCEPTABLE)
            user = User.objects.create_user(
                employee_id, email, name, team, gender, phone, password
            )
            for i in role:
                r = Role.objects.get(id=i)
                user.role.add(r)
            return Response({"message": "Success", "data": self.serializer_class(user).data},
                            status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='technology')
    def technology(self, request):
        try:
            technology = request.data.get('technology')
            if technology:
                technology = [tech for tech in technology if tech and tech != 'null']
                request.user.technology = technology
                request.user.save()
                return Response({"message": "Technologies Updated"}, status=status.HTTP_202_ACCEPTED)
            return Response({"message": "Input is empty"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"message": "File format not supported"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"message": "Success", "data": data}, status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='profile')
    def profile(self, request):
        try:
            user_id = request.data.get('user_id')
            role_ids = request.data.get('role_id', [])
            team_id = request.data.get('team_id', None)
            if 'superadmin' in request.user.roles:
                user = get_object_or_404(User, id=user_id)
                desc = ""
                if team_id:
                    prev_team = user.team.name
                    team = get_object_or_404(Team, id=team_id)
                    user.team = team
                    desc += f"{request.user.employee_name} changed {user.employee_name}'s team from {prev_team} to {team.name} "
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
                return Response({"message": f"{user.employee_name}'s Profile updated"}, status=status.HTTP_202_ACCEPTED)
            return Response({"message": DONT_HAVE_ACCESS}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='account')
    def account(self, request):
        try:
            user_id = request.data.get('user_id')
            account_login = request.data.get('active', None)
            if request.user.is_superuser:
                user = get_object_or_404(User, id=user_id)
                if account_login is not None:
                    user.account_login = account_login
                    user.is_active = account_login
                    user.save()
                else:
                    return Response({"message": "Parameter is not correct", "error": str(account_login)},
                                    status=status.HTTP_400_BAD_REQUEST)

            if account_login:
                message = "Activated"
            else:
                message = "Deactivated"
            return Response({"message": f"Account {message}"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='profile_activity')
    def profile_activity(self, request):
        try:
            user_id = request.GET.get('employee')
            content_type = ContentType.objects.get(model='user')
            activities = Activity.objects.filter(content_type=content_type, activity_type="updated", object_id=user_id
                                                 ).order_by('-created').values()
            all_activities = []
            for activity in activities:
                if 's team from ' in activity['desc'] or 'changed role to ' in activity['desc']:
                    all_activities.append(activity)

            return Response({"data": all_activities}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='me')
    def me(self, request):
        try:
            cookie_value = request.META.get('HTTP_X_ID_TOKEN', None)
            devices_cookies = Devices.objects.filter(cookies_value=cookie_value).first()
            location = Location.objects.filter(device=devices_cookies).first()
            return Response({"data": UserDashboardSerializer(request.user).data,
                             "is_location_recoded": True if location else False}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='role')
    def role(self, request):
        try:
            roles = Role.objects.all().values('id', 'name', 'display_name')
            return Response({"data": roles}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='team')
    def team(self, request):
        try:
            query = request.GET.get('query', None)
            department = request.GET.get('dept', None)
            if query == 'all':
                teams = Team.objects.exclude(dept='marketing').values('id', 'name')
            elif department:
                teams = Team.objects.filter(dept=department).values('id', 'name')
            else:
                teams = Team.objects.all().values('id', 'name')
            return Response({"data": teams}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        try:
            current_password = request.data.get('cur_password')
            new_password = request.data.get('new_password')
            if request.user.check_password(current_password):
                is_valid = valid_password(new_password)
                if is_valid:
                    request.user.set_password(new_password)
                    request.user.save()
                    return Response({"message": "password updated"}, status=status.HTTP_200_OK)
                else:
                    return Response({'message': 'Password is not in valid format'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='directory')
    def directory(self, request):
        first, last = get_page_limits(request)
        try:
            if 'superadmin' in request.user.roles:
                query = request.GET.get('query', None)
                team = request.GET.get('team', None)
                role = request.GET.get('roles', None)
                users = User.objects.all().exclude(role__name='consultant')
                if query:
                    query = query.lstrip().replace(':amp:', '&')
                    users = users.filter(
                        Q(employee_name__icontains=query) |
                        Q(email__iexact=query)
                    )
                if team:
                    users = users.filter(team__id=team)
                if role:
                    users = users.filter(role__id=role)
                total = users.count()
                serializer = UserDirectorySerializer(users[first:last], many=True)
                return Response({"data": serializer.data, "total": total}, status=status.HTTP_200_OK)
            return Response({"message": DONT_HAVE_ACCESS}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=False, url_path='update')
    def update_user(self, request):
        try:
            data = request.data
            employee = request.user
            employee.phone = data.get('phone', employee.phone)
            employee.shift = data.get('shift', employee.shift)
            employee.gender = data.get('gender', employee.gender)
            employee.employee_name = data.get('employee_name', employee.employee_name)
            employee.team = Team.objects.get(name=data.get('team', employee.team.name))
            employee.technology = json.loads(data.get('technology')) if data.get('technology') else employee.technology
            tech = employee.technology
            if tech:
                if 'null' in tech:
                    tech.remove('null')
                if None in tech:
                    tech.remove(None)
            employee.technology = tech
            if request.FILES.get('image'):
                employee.avatar = request.FILES['image']
            employee.save()
            return Response({"message": "User Profile Updated"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='shifts')
    def shift_timings(self, request):
        try:
            data = User.SHIFT_CHOICE
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='get_projects')
    def projects(self, request):
        try:
            projects = ProjectSupport.objects.filter(
                statuses__frequency__in=['active', 'less_active'], end=None,
                statuses__is_current=True, is_proxy_support=False, support=request.user
            ).exclude(project__statuses__is_current=True,
                      project__statuses__status__istartswith='terminated' or 'cancelled').annotate(
                employer=F('project__employer'),
                consultant_name=F('project__submission__consultant_marketing__consultant__name'),
                client=F('project__submission__client'), vendor=F('project__submission__lead__vendor_company__name'),
            ).values("project_id", "client", "consultant_name", "employer", "vendor")

            return Response({"data": projects}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='projects')
    def verify_project(self, request):
        try:
            vendor = request.GET['vendor']
            client = request.GET['client']
            consultant = request.GET['consultant']
            project = Project.objects.filter(
                submission__lead__vendor_company__name__icontains=vendor,
                submission__consultant_marketing__consultant__name=consultant,
                submission__client__icontains=client, statuses__is_current=True,
                statuses__status__in=['new', 'joined', 'signed', 'received', 'extended', 'on_boarded']
            ).annotate(
                consultant_name=F('submission__consultant_marketing__consultant__name'),
                client=F('submission__client'), vendor=F('submission__lead__vendor_company__name'),
            ).values("id", "client", "consultant_name", "employer", "vendor")
            if not project:
                return Response({"data": [], "message": "No Project Found"}, status=status.HTTP_200_OK)
            return Response({"data": project, "message": "Project Found"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='associated_to')
    def associated(self, request):
        try:
            assigned_teams = []
            primary_team = request.user.team
            associated_teams = request.user.associated_to.all().values('id', 'name')
            if primary_team not in request.user.associated_to.all() and primary_team.dept != 'Recruitment':
                assigned_teams.append({"id": primary_team.id, "name": primary_team.name})
            assigned_teams.extend(associated_teams)
            return Response({"data": assigned_teams}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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

        users = User.objects.filter(email__iexact=email, is_active=True)

        active_user_found = False
        password_usable_user_found = False

        for user in users:
            if user.is_active:
                active_user_found = True
                if user.has_usable_password():
                    password_usable_user_found = True
                    break

        # No active user found, raise a validation error
        if not active_user_found:
            raise exceptions.ValidationError({
                'message': [_(
                    "There is no active user associated with this e-mail address")],
            })

        if active_user_found and not password_usable_user_found:
            raise exceptions.ValidationError({
                'message': [_(
                    "The password for the active user cannot be changed")],
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
                # res, error = user.send_mail(mail_data)
                res, mail_sent, from_email = send_email(mail_data, config.APP_ADMIN, request)
                if mail_sent:
                    return Response({"message": f"Mail sent on {user.email}", "data": res}, status=status.HTTP_200_OK)
                else:
                    write_info(message=res, function='token_request')
                    return Response(
                        {"message": "Something went wrong", "error": str(res)}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response({"message": "User is not active"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)

    def valid_token(self, data):
        """
            Validate a password reset token.

            This function validates a password reset token by checking its expiry
            and existence in the database. This method also validates the data type of
            token and password. It returns the reset token object (if valid), the password (if provided),
            and a flag indicating if the token is valid.

            Args:
                self: The current object instance.
                data (dict): The data containing the password reset token and password.

            Returns:
                Three variables: Reset token object (if valid), Password (if provided),
                and a flag indicating if the token is valid.
        """

        try:
            serializer = self.pass_serializer_class(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            if data.get('password'):
                password = serializer.validated_data['password']
            if data.get('token'):
                token = serializer.validated_data['token']

            password_reset_token_validation_time = get_token_expiry_time()

            reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

            if reset_password_token is None:
                return reset_password_token if reset_password_token else '', \
                    password if data.get('password') else '', False

            expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

            if timezone.now() > expiry_date:
                reset_password_token.delete()
                return reset_password_token if reset_password_token else '', \
                    password if data.get('password') else '', False
            return reset_password_token if reset_password_token else '', \
                password if data.get('password') else '', True
        except Exception as error:
            write_exception(message=error)
            return False

    @action(methods=['post'], detail=False, url_path='token_verify')
    def token_verify(self, request):
        """
            Verify a password reset token.

            This api verifies a password reset token by calling the `valid_token` function
            and returns a response based on the validity of the token.

            Args:
                self: The current object instance.
                request: The HTTP request object.

            Returns:
                Response: The response indicating the result of token verification.
        """
        try:
            reset_password_token, password, valid = self.valid_token(request.data)
            if valid:
                return Response({'message': 'OTP Verified'}, status=status.HTTP_200_OK)
            return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        """
            Confirm token and change the password.

            This api confirms a password reset token by calling the `valid_token` function,
            and if the token is valid, it changes the user's password and deletes the
            reset password token from the database.

            Args:
                self: The current object instance.
                request: The HTTP request object.

            Returns:
                Response: The response indicating the result of change password.
        """
        try:
            reset_password_token, password, valid = self.valid_token(request.data)
            if valid:
                is_valid = valid_password(request.data.get('password'))
                if is_valid:
                    reset_password_token.user.set_password(password)
                    reset_password_token.user.save()
                    ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()
                    return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
                else:
                    return Response({'message': 'Password is not in valid format'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"data": data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"data": serializer.data, "message": "Asset added"}, status=status.HTTP_201_CREATED)
            return Response({"message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"data": serializer.data, "message": "Asset updated"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            asset = get_object_or_404(Asset, id=kwargs.get('pk'), owner=request.user)
            asset.is_deleted = True
            asset.save()
            desc = f"{request.user.employee_name.title()} deleted {asset.asset_type} asset"
            create_activity(asset.id, 'asset', request.user, desc, 'deleted')
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(methods=['put'], detail=False, url_path='share')
    def share(self, request):
        users = request.data.get('users', [])
        assets = request.data.get('assets', [])
        try:
            if len(assets) < 1:
                return Response({"message": "Please select Asset"}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"message": "Asset shared"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='un_share')
    def un_share(self, request, pk):
        try:
            asset = get_object_or_404(Asset, id=pk, owner=request.user)
            user = User.objects.get(id=request.data.get('user'))
            asset.shared_to.remove(user)
            desc = f"{request.user.employee_name} Unshared {user.employee_name} from {asset.asset_type} asset"
            create_activity(asset.id, 'asset', request.user, desc, 'updated')
            serializer = self.serializer_class(asset)
            return Response({"data": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"message": "File format not supported"}, status=status.HTTP_400_BAD_REQUEST)
            if not df.empty:
                created, updated, failed = 0, 0, 0
                if not {'Username', 'Provider', 'Password', 'Asset Type', 'Email', 'Technology',
                        'Remarks', 'Phone Number', 'Alternate Email', 'Alternate Number'
                        }.issubset(set(df.columns)):
                    return Response({"message": "Invalid Data Format"}, status=status.HTTP_404_NOT_FOUND)

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
                _, result, mId = send_email(mail_data, "product@consultadd.com", request=request)
                message = "mail send fail"
                if result:
                    message = "mail sent successfully"
                return Response({"message": "Upload Complete", "count": mail_data['context'], "mail": message},
                                status=status.HTTP_201_CREATED)
            return Response({"message": "Empty File"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"data": result_list}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='calendar_info')
    def calendar_info(self, request):
        try:
            data = request.query_params.get('data')
            if data:
                json_data = json.loads(data)
                if 'emails' not in json_data:
                    return Response({"message": "Please select user"}, status=status.HTTP_400_BAD_REQUEST)
                if len(json_data["emails"]) < 1:
                    return Response({"message": "Please select user"}, status=status.HTTP_400_BAD_REQUEST)

                # 2021-02-11T09:00:00 datetime format (EST)
                tz_est = tz.gettz('US/Eastern')
                if json_data.get('start', None):
                    start = f"{datetime.strptime(json_data['start'], '%Y-%m-%d').strftime('%Y-%m-%dT00:00:00Z')}"
                else:
                    start = f"{datetime.now().astimezone(tz_est).strftime('%Y-%m-%dT00:00:00Z')}"

                if json_data.get('end'):
                    end = f"{datetime.strptime(json_data['end'], '%Y-%m-%d').strftime('%Y-%m-%dT23:59:59Z')}"
                elif json_data.get('start'):
                    end = f"{datetime.strptime(json_data['start'], '%Y-%m-%d').strftime('%Y-%m-%dT23:59:59Z')}"
                else:
                    end = f"{datetime.now().astimezone(tz_est).strftime('%Y-%m-%dT23:59:59Z')}"
            else:
                return Response({"message": "Provide correct input"}, status=status.HTTP_400_BAD_REQUEST)

            payload = {
                "start": start, "end": end, "user_emails": json_data["emails"]
            }
            calendar = GoogleCalendar()
            resp, msg = calendar.get_calendar_schedule(payload, request)
            if msg != 'error':
                return Response({"data": resp}, status=status.HTTP_200_OK)
            return Response({"message": resp['message'], "error": resp['error']['error']},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
                return Response({"message": f"User handed over to {handover_to_name}"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

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
                    return Response({"message": f"User handed over to {handover_to_name}"},
                                    status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({"message": "Handover not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            if 'superadmin' in request.user.roles:
                user_id = kwargs.get('pk', None)
                if not user_id:
                    return Response({"message": f"User is not provided"}, status=status.HTTP_400_BAD_REQUEST)
                user = get_object_or_404(User, id=user_id)
                handovers = Handover.objects.filter(user_id=user_id)
                if handovers:
                    desc = f"{request.user.employee_name} removed handover of {user.employee_name}"
                    create_activity(user.id, 'user', request.user, desc, 'update')
                    handovers.delete()
                    return Response({"message": f"User handover removed"}, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({"message": "Handover not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Method PATCH not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# Route - /login/
class LoginViewSet(GenericViewSet, CreateModelMixin, DestroyModelMixin):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        result = {}
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            team = request.data.get('team', None)
            if isinstance(team, str):
                team = get_object_or_404(Team, name=team)
            user = User.objects.create_user(
                team=team,
                name=request.data.get('name'),
                email=request.data.get('email'),
                phone=request.data.get('phone', None),
                gender=request.data.get('gender').lower(),
                password=request.data.get('password').strip(),
                employee_id=int(request.data.get('employee_id')),
            )
            if not request.data.get('keep_active'):
                user.is_active = False
                user.save()
            for role in request.data.get("role", []):
                user_role = get_object_or_404(Role, name=role)
                user.role.add(user_role)
                user.save()

            return Response({"message": "User Created in Log1", "user_id": user.id}, status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": result, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='bulk_create')
    def create_bulk(self, request):
        result = {}
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            roles, record_list = [], []
            records = request.data.get('data')
            for record in records:
                is_active = True if record.get('log1') == 'TRUE' or record.get('log1') is True else False
                if record.get('role', []):
                    roles.append(record.get('role', []).replace(' ', '').split(","))
                record_list.append(User(
                    is_active=is_active,
                    email=record.get('email'),
                    phone=record.get('phone'),
                    employee_name=record.get('name'),
                    gender=record.get('gender', 'male'),
                    username=int(record.get('employee_id')),
                    employee_id=int(record.get('employee_id')),
                    password=make_password(record.get('password', 'consultadd')),
                    team=Team.objects.filter(
                        name=record.get('team').strip().capitalize()
                    ).first() if isinstance(record.get('team'), str) else None
                ))
            users = User.objects.bulk_create(record_list)
            for user, role in zip(record_list, roles):
                for role_name in role:
                    role_object = Role.objects.filter(name=role_name.lower().strip()).first()
                    if role_object:
                        user.role.add(role_object)
            users = [user.employee_id for user in users]
            result["users"] = users
            result["msg"] = f"{len(users)} users  Created"

            return Response({"result": result}, status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": result, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
            user = get_object_or_404(User, id=kwargs.get('pk'))
            if user:
                user.delete()
                return Response({"message": "User Removed"}, status=status.HTTP_204_NO_CONTENT)
            return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['delete'], detail=False, url_path='bulk_delete')
    def delete_bulk(self, request, ):
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            users = User.objects.filter(employee_id__in=request.data.get('users', [])).delete()
            data = {"msg": f"{len(users)} users  removed from beats"}
            return Response({"result": data}, status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='update_user')
    def update_user(self, request, pk):
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            user = User.objects.filter(employee_id=pk).first()
            user_previous_data = User.objects.filter(employee_id=pk).values()

            if not user:
                return Response({"message": "User not exists"}, status=status.HTTP_400_BAD_REQUEST)

            user_roles = request.data.get('role', [])
            user_previous_role = user.role.all()
            if user_roles and user_roles != user_previous_role:
                user.role.remove(*user_previous_role)
                for role in user_roles:
                    user_role = Role.objects.filter(name=role).first()
                    user.role.add(user_role)
            user.email = request.data.get('email', user.email)
            user.phone = request.data.get('number', user.phone)
            user.gender = request.data.get('gender', user.gender)
            user.is_active = request.data.get('is_active', user.is_active)
            user.employee_name = request.data.get('name', user.employee_name)
            user.employee_id = request.data.get('employee_id', user.employee_id)
            user.team = Team.objects.get(name=request.data['team']) if request.data.get('team') else user.team
            if user_previous_data[0].is_active != user.is_active:
                user.account_login = user.is_active
            user.save()
            return Response({'data': user_previous_data, 'role': user_previous_role.values(),
                             "result": "User updated on log1 successfully"}, status=status.HTTP_201_CREATED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='update_access')
    def update_access(self, request, pk):
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            user = User.objects.filter(employee_id=pk).first()
            if not user:
                return Response({"message": "User not found in log1"}, status=status.HTTP_400_BAD_REQUEST)
            roles = user.role.filter().values_list('name', flat=True)

            data = request.data.get('log1', {})
            if not data:
                return Response({"message": "No change recorded"}, status=status.HTTP_204_NO_CONTENT)

            is_active = data.get("is_active", None)
            team = request.data.get('team')
            if is_active is not None:
                if is_active:
                    user.is_active = True
                    is_role_changed = False if roles == data.get("role") else True
                    if (not roles) or is_role_changed:
                        user.role.remove(*roles)
                        for role in data.get("role"):
                            user_role = Role.objects.filter(name=role).first()
                            user.role.add(user_role)
                    if not user.team:
                        user.team = Team.objects.get(name=team)
                else:
                    user.is_active = False
                user.save()
                return Response({"message": "User access updated"}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({"message": "No change recorded"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['put'], detail=True, url_path='deactivate')
    def deactivate(self, request, pk):
        try:
            api_key = request.data.get('log1_api_key', None)
            if not api_key:
                return Response({"message": "Api Key not found"}, status=status.HTTP_401_UNAUTHORIZED)
            if not APIKey.objects.is_valid(api_key):
                return Response({"message": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            user = User.objects.filter(employee_id=pk).first()
            if not user:
                return Response({"message": "User not found in log1"}, status=status.HTTP_400_BAD_REQUEST)
            if user.is_active:
                user.is_active = False
                user.account_login = False
                user.save()
                return Response({"message": "Deactivated Successfully"}, status=status.HTTP_202_ACCEPTED)
            return Response({"message": "No change required"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Route - /calendar_info/
class DefaultCalendarViewSets(GenericViewSet, CreateModelMixin, ListModelMixin):
    serializer_class = UserSerializer
    queryset = DefaultCalendar.objects.all()
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            if type(request.data['emails']) is list:
                obj, msg = DefaultCalendar.objects.get_or_create(user=request.user)
                obj.emails = request.data['emails']
                obj.save()
                return Response({"message": "Emails set as default"}, status=status.HTTP_200_OK)

            return Response({"message": "No emails provided to set set default"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='get_default')
    def default(self, request, *args, **kwargs):
        try:
            default = DefaultCalendar.objects.filter(user=request.user).first()
            if not default:
                return Response({"data": []}, status=status.HTTP_200_OK)
            if not default.emails:
                return Response({"data": []}, status=status.HTTP_200_OK)
            data = {"emails": default.emails}
            start = f"{datetime.now().astimezone(tz.gettz('US/Eastern')).strftime('%Y-%m-%dT00:00:00Z')}"
            end = f"{datetime.now().astimezone(tz.gettz('US/Eastern')).strftime('%Y-%m-%dT23:59:59Z')}"
            payload = {
                "start": start, "end": end, "user_emails": data['emails']
            }
            calendar = GoogleCalendar()
            resp, msg = calendar.get_calendar_schedule(payload, request)
            if msg != 'error':
                return Response({"data": resp}, status=status.HTTP_200_OK)
            return Response({"message": resp['message'], "error": resp['error']['error']},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Route - /employee_certificate/
class CertificateViewSets(GenericViewSet, CreateModelMixin, ListModelMixin, UpdateModelMixin, DestroyModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = CertificateInfo.objects.all()
    serializer_class = CertificateInfoSerializer
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            certificates = CertificateInfo.objects.filter(employee=request.user)
            serializer = self.serializer_class(certificates, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        try:
            certificate_name = request.data.get('certificate_name', None)
            organization = request.data.get('organization', None)
            certificate = Certificate.objects.filter(name=certificate_name, issued_by=organization).first()
            if not certificate:
                available_certificate = Certificate.objects.filter(
                    name__icontains=certificate_name, issued_by=organization
                )
                if available_certificate:
                    return Response({"message": "Certificate Info Already Exists"}, status=status.HTTP_400_BAD_REQUEST)
                certificate = Certificate.objects.create(name=certificate_name, issued_by=organization)
            CertificateInfo.objects.create(
                expiry_date=request.data.get('expiry_date', None), issued_date=request.data.get('issued_date'),
                credential_id=request.data.get('credential_id', None), has_expiry=request.data.get('has_expiry'),
                certificate=certificate, employee=request.user, credential_url=request.data.get('credential_url', None)
            )
            user = get_object_or_404(User, id=request.user.id)
            user.have_certificate = True
            user.save()
            return Response({"message": "Certificate Added"}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            certificate_info = get_object_or_404(CertificateInfo, id=kwargs.get('pk'))
            serializer = self.serializer_class(certificate_info, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Certificate Info Updated"}, status=status.HTTP_202_ACCEPTED)
            return Response({"message": "Please provide correct certificate info"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            certificate_info = get_object_or_404(CertificateInfo, id=kwargs.get('pk'))
            certificate_info.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(['PUT'], detail=False, url_path='mark_certificate')
    def mark_certificate(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=request.user.id)
            user.have_certificate = request.data.get('have_certificate')
            user.save()
            return Response({"data": "Data updated successfully"}, status=status.HTTP_202_ACCEPTED)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(['GET'], detail=False, url_path='get_all')
    def get_all(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', None)
            organization = json.loads(request.GET.get('organization', 'false'))
            organization_name = request.GET.get('organization_name', 'false')
            certificates = Certificate.objects.all()
            if organization:
                certificates = certificates.filter().order_by('issued_by') \
                    .distinct('issued_by').values_list('issued_by', flat=True)
                return Response({"data": certificates}, status=status.HTTP_200_OK)

            if organization_name:
                certificates = certificates.filter(issued_by=organization_name)
            if query:
                certificates = certificates.filter(name__icontains=query.lstrip().replace(':amp:', '&'))
            certificates = certificates.filter().values('id', 'name', 'issued_by')
            return Response({"data": certificates}, status=status.HTTP_200_OK)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)
