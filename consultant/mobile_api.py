import os
from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from constance import config
from project.models import Project
from utils_app.mailing import send_email
from log1.utils import write_exception, write_info
from consultant.permissions import ConsultantIsAuthenticated
from consultant.serializers import ConsultantLoginSerializer
from employee.models import clear_expired, get_token_expiry_time
from employee.serializers import EmailSerializer, PasswordTokenSerializer
from consultant.authentication import consultant_authenticate, ConsultantTokenAuthentication
from consultant.models import Consultant, ConsultantToken, ConsultantResetPasswordToken, FCMDevice


# API for Mobile App
# Route - /consultant_auth/
class ConsultantAuthViewSet(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer

    @action(methods=['post'], detail=False, url_path='register')
    def register(self, request):
        """
            Consultant Register
            :param request, email, name, company, website, designation
        """
        try:
            name = request.data.get('name')
            company = request.data.get('company')
            website = request.data.get('website')
            email = request.data.get('email').strip()
            designation = request.data.get('designation')
            customer_mail_data = {
                'to': [email],
                'cc': [],
                'bcc': [config.TIMESHEET_APP_ADMIN],
                'subject': 'Signup on Consultadd Time Track App',
                'template': '../templates/con_signup_mail.html',
                'context': {
                    'name': name
                },
            }

            send_email(customer_mail_data, "log1@consultadd.com")

            mail_data = {
                'to': [config.TIMESHEET_APP_ADMIN],
                'cc': [],
                'bcc': [],
                'subject': f'{name} Signed up on Consultadd Time Track App',
                'template': '../templates/signup_mail.html',
                'context': {
                    'name': name,
                    'email': email,
                    'website': website,
                    'company': company,
                    'designation': designation,
                },
            }
            send_email(mail_data, "log1@consultadd.com")
            return Response({"result": "mail sent"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({'error': str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password, uuid, fcm_token, device_type
        """
        email = request.data.get('email').lower().strip()
        if email:
            consultant = get_object_or_404(Consultant, email__iexact=email)
        else:
            return Response({"error": "Email is Empty"}, status=400)
        consultant = consultant_authenticate(email=consultant.email, password=request.data.get('password').strip())
        if consultant:
            uuid = request.data.get('uuid', '')
            try:
                token, created = ConsultantToken.objects.get_or_create(consultant=consultant, uuid=uuid)
                content_type = ContentType.objects.get(model='consultanttoken')
                fcm_device, created = FCMDevice.objects.get_or_create(
                    device_id=request.data.get('fcm_token', None),
                    type=request.data.get('device_type', 'android'),
                    content_type=content_type
                )
                fcm_device.object_id = token.key
                fcm_device.save()
                project_data = Project.objects.filter(
                    consultant=consultant,
                    statuses__status='joined',
                    statuses__is_current=True
                ).annotate(
                    client=F('submission__client'),
                ).order_by('-id').values('id', 'start_date', 'client', 'employer')
                data = {
                    'token': token.key,
                    'id': consultant.id,
                    'name': consultant.name,
                    'project': project_data,
                    'email': consultant.email,
                    'is_active': consultant.is_active,
                    'first_login': consultant.first_login,
                }
                return Response({"result": data}, status=202)
            except Exception as error:
                write_exception(error, request)
                return Response({"error": str(error)}, status=400)
        return Response({"error": "Incorrect Email Id OR Password"}, status=400)


# API for Mobile App
# Route - /consultant_app/
class ConsultantAppViewSet(ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            queryset = Consultant.objects.all()
            serializer = self.serializer_class(queryset, many=True)
            return Response({"results": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        try:
            first_login = request.GET.get('first_login', None)
            new_password = request.data.get('new_password', None)
            consultant = request.user
            if first_login and new_password:
                if consultant.check_password(new_password):
                    return Response({"error": "Please use new password", "error_in": "new"},
                                    status=400)
                consultant.set_password(new_password)
                consultant.first_login = False
            else:
                current_password = request.data.get('current_password', None)
                if current_password and consultant.check_password(current_password):
                    if consultant.check_password(new_password):
                        return Response({"error": "Please use new password", "error_in": "new"},
                                        status=400)
                    consultant.set_password(new_password)
                else:
                    return Response({"error": "Wrong Current Password", "error_in": "current"},
                                    status=400)
            consultant.save()
            return Response({"result": "Password Updated"}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)

    @action(methods=['delete'], detail=False, url_path='logout')
    def logout(self, request):
        try:
            uuid = request.META.get('HTTP_UUID', b'')
            token = get_object_or_404(ConsultantToken, key=request.auth, uuid=uuid)
            token.delete()
            return Response(status=204)
        except Exception as error:
            write_exception(error, request)
            return Response({"error": str(error)}, status=400)


# API for Mobile App
# Route - /consultant_password/
class ConsultantResetPasswordViewSet(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    serializer_class = EmailSerializer
    queryset = Consultant.objects.all()

    @action(methods=['post'], detail=False, url_path='token_request')
    def token_request(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        password_reset_token_validation_time = get_token_expiry_time()

        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        clear_expired(now_minus_expiry_time)

        consultants = Consultant.objects.filter(email__iexact=email)

        active_user_found = False
        for consultant in consultants:
            if consultant.is_active and consultant.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            raise exceptions.ValidationError({
                'email': [
                    "There is no active user associated with this e-mail address or the password can not be changed"],
            })
        ip = request.META['REMOTE_ADDR']
        for consultant in consultants:
            if consultant.is_active and consultant.has_usable_password():
                if consultant.password_reset_tokens.all().count() > 0:
                    token = consultant.password_reset_tokens.all()[0]
                else:
                    token = ConsultantResetPasswordToken.objects.create(
                        consultant=consultant,
                        user_agent=request.META['HTTP_USER_AGENT'],
                        ip_address=ip if ip else '127.0.0.1'
                    )
                if os.environ.get('ENV', 'local') == 'prod':
                    to = [consultant.email]
                else:
                    to = ['sarang.m@consultadd.com']
                mail_data = {
                    'to': to,
                    'cc': [],
                    'bcc': [],
                    'subject': 'Reset Log1 Password',
                    'template': '../templates/con_password_reset.html',
                    'context': {
                        'name': consultant.name,
                        'token': token.key,
                    },
                }
                res, error = consultant.send_mail(mail_data)
                if error == 'error':
                    write_info(message=res, function='token_request')
                    return Response({'error': str(res)}, status=400)
        return Response({'status': 'OK'}, status=200)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        serializer = PasswordTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        password_reset_token_validation_time = get_token_expiry_time()

        reset_password_token = ConsultantResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({'status': 'incorrect token'}, status=404)

        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

        if timezone.now() > expiry_date:
            reset_password_token.delete()
            return Response({'status': 'token expired'}, status=404)

        reset_password_token.consultant.set_password(password)
        reset_password_token.consultant.save()

        # Delete all password reset tokens for this user
        ConsultantResetPasswordToken.objects.filter(consultant=reset_password_token.consultant).delete()

        return Response({'status': 'OK'}, status=200)
