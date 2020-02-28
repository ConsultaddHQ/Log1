from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from employee.serializers import UserSerializer
from employee.models import User


class ImpersonateViewSets(GenericViewSet, ListModelMixin, CreateModelMixin):
    # check if user is a superuser and has rights to impersonate
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def create(self, request, *args, **kwargs):
        try:
            if request.user.is_superuser:
                employee_id = request.data['employee_id']
                # check if requested impersonated user exists
                user_exists = User.objects.filter(employee_id=employee_id)
                if user_exists:
                    user = user_exists.first()
                    token1, created = Token.objects.get_or_create(user=user)
                    # create user token for impersonation
                    return Response({"result": {
                        'current_user': request.user.employee_id,
                        'impersonated_user': user.employee_id,
                        'user_id': user.id,
                        'success': True,
                        'token': token1.key
                    }}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"result": {
                        'message': 'User not Exist'
                    }}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"result": {
                    'message': 'Unauthorised Access'
                }}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as error:
            response = Response({"result": {
                'success': False,
                'message': 'Unauthorised Access'
            }})
            response.status_code = 403
            return response