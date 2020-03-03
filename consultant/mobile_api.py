import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from project.models import Project
from consultant.serializers import *
from consultant.auth import consultant_authenticate
from consultant.permissions import ConsultantIsAuthenticated
from employee.models import get_password_reset_token_expiry_time
from employee.serializers import EmailSerializer, PasswordTokenSerializer
from consultant.authentication import ConsultantTokenAuthentication, get_consultant

logger = logging.getLogger(__name__)


# API for Mobile App
class ConsultantAuthViewSets(GenericViewSet):
    permission_classes = ()
    authentication_classes = ()
    queryset = Consultant.objects.all()
    serializer_class = ConsultantLoginSerializer

    @action(methods=['post'], detail=False, url_path='register')
    def register(self, request):
        """
            User Register
            :param request, email, password, employee_id, name, phone, gender, team, role
        """
        try:
            email = request.data.get('email')
            password = request.data.get('password').strip()

            queryset = Consultant.objects.filter(email__exact=email)
            if queryset:
                consultant = queryset.first()
                consultant.set_password(password)
                consultant.is_active = True
                consultant.save()

                return Response({"result": "Success"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Consultant Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.error(error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        """
            Normal Login
            :param request, email, password
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
                    statuses_status='joined'
                ).annotate(
                    client=F('submission__client'),
                    employer=F('submission__employer')
                ).values('id', 'start_date', 'client', 'employer')
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
class ConsultantAppViewSets(ListModelMixin, GenericViewSet):
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
        consultant = get_consultant(request)
        if consultant.check_password(new_password):
            return Response({"error": "Please use new password"}, status=status.HTTP_400_BAD_REQUEST)
        if first_login and new_password:
            consultant.set_password(new_password)
            consultant.first_login = False
        else:
            current_password = request.data.get('current_password', None)
            if current_password:
                consultant.set_password(new_password)
            else:
                return Response({"error": "Wrong Password"}, status=status.HTTP_400_BAD_REQUEST)
        consultant.save()
        return Response({"result": "password updated"}, status=status.HTTP_200_OK)

    @action(methods=['delete'], detail=False, url_path='logout')
    def logout(self, request):
        """
            Logout for authenticated user
        """
        uuid = request.META.get('HTTP_UUID', b'')
        token = get_object_or_404(ConsultantToken, key=request.auth, uuid=uuid)
        fcm_token = FCMDevice.objects.filter(content_type__model='consultanttoken', object_id=token.key)
        token.delete()
        fcm_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# API for Mobile App
class ConsultantResetPasswordViewSets(GenericViewSet):
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
                mail_data = {
                    'to': ['aditi.so@consultadd.in'],
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
