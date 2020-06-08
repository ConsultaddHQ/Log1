import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from consultant.serializers import *
from consultant.auth import consultant_authenticate
from consultant.permissions import ConsultantIsAuthenticated
from employee.models import get_password_reset_token_expiry_time
from consultant.authentication import ConsultantTokenAuthentication
from employee.serializers import EmailSerializer, PasswordTokenSerializer

logger = logging.getLogger(__name__)


# API for Mobile App
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
                'bcc': ['aditi.so@consultadd.in'],
                'subject': 'Signup on Consultadd Time Track App',
                'template': '../templates/con_signup_mail.html',
                'context': {
                    'name': name
                },
            }

            send_email(customer_mail_data, "log1@consultadd.com")

            mail_data = {
                'to': ['aditi.so@consultadd.in'],
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
            return Response({"result": "mail sent"}, status=status.HTTP_200_OK)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password, uuid, fcm_token, device_type
        """
        email = request.data.get('email').lower()
        if email:
            consultant = get_object_or_404(Consultant, email=email)
        else:
            return Response({"error": "Email is Empty"}, status=status.HTTP_400_BAD_REQUEST)
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
                    employer=F('submission__employer')
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
                return Response({"result": data}, status=status.HTTP_202_ACCEPTED)
            except Exception as error:
                logger.error(error)
                return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        logger.error("Incorrect Email Id OR Password")
        return Response({"error": "Incorrect Email Id OR Password"}, status=status.HTTP_400_BAD_REQUEST)


# API for Mobile App
class ConsultantAppViewSet(ListModelMixin, GenericViewSet):
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer
    permission_classes = (ConsultantIsAuthenticated,)
    authentication_classes = (ConsultantTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        queryset = Consultant.objects.all()
        serializer = self.serializer_class(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='change_password')
    def change_password(self, request):
        first_login = request.query_params.get('first_login', None)
        new_password = request.data.get('new_password', None)
        consultant = request.user
        if first_login and new_password:
            if consultant.check_password(new_password):
                return Response({"error": "Please use new password", "error_in": "new"},
                                status=status.HTTP_400_BAD_REQUEST)
            consultant.set_password(new_password)
            consultant.first_login = False
        else:
            current_password = request.data.get('current_password', None)
            if current_password and consultant.check_password(current_password):
                if consultant.check_password(new_password):
                    return Response({"error": "Please use new password", "error_in": "new"},
                                    status=status.HTTP_400_BAD_REQUEST)
                consultant.set_password(new_password)
            else:
                return Response({"error": "Wrong Current Password", "error_in": "current"},
                                status=status.HTTP_400_BAD_REQUEST)
        consultant.save()
        return Response({"result": "Password Updated"}, status=status.HTTP_200_OK)

    @action(methods=['delete'], detail=False, url_path='logout')
    def logout(self, request):
        """
            Logout for authenticated user
        """
        uuid = request.META.get('HTTP_UUID', b'')
        token = get_object_or_404(ConsultantToken, key=request.auth, uuid=uuid)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# API for Mobile App
class ConsultantResetPasswordViewSet(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
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

        consultants = Consultant.objects.filter(email__iexact=email)

        active_user_found = False
        for consultant in consultants:
            if consultant.is_active and consultant.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            logger.info("User is not active")
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
                    to = ['aditi.so@consultadd.in', 'sarang.m@consultadd.in', 'anikesh.consultadd@gmail.com']
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
                    logger.error(res)
                    return Response({'error': str(res)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'OK'}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='confirm_password')
    def confirm_password(self, request):
        serializer = self.pass_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        reset_password_token = ConsultantResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({'status': 'incorrect token'}, status=status.HTTP_404_NOT_FOUND)

        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)

        if timezone.now() > expiry_date:
            reset_password_token.delete()
            return Response({'status': 'token expired'}, status=status.HTTP_404_NOT_FOUND)

        reset_password_token.consultant.set_password(password)
        reset_password_token.consultant.save()

        # Delete all password reset tokens for this user
        ConsultantResetPasswordToken.objects.filter(consultant=reset_password_token.consultant).delete()

        return Response({'status': 'OK'}, status=status.HTTP_200_OK)
