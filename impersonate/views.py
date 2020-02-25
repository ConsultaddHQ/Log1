from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication


class ImpersonateView(APIView):
    # check if user is a superuser and has rights to impersonate
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        if request.user.is_superuser:
            return Response({
                'message': 'Impersonation Starts'
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({
                'message': 'UnAuthorised Access'
            }, status=status.HTTP_401_UNAUTHORIZED)


class ImperEnv(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        User = get_user_model()
        try:
            employee_id = request.data['employee_id']
            # check if requested impersonated user exists
            user_exists = User.objects.filter(employee_id=employee_id).exists()
            user = User.objects.filter(employee_id=employee_id)[0]
            if user_exists:
                token1, created = Token.objects.get_or_create(user=user)
                # create user token for impersonation
                return Response({
                    'current_user': request.user.employee_id,
                    'impersonated_user': user.employee_id,
                    'user_id': user.id,
                    'success': True,
                    'token': token1.key
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message': 'User not Exist'
                }, status=status.HTTP_400_BAD_REQUEST)
        except:
            response = Response({
                'success': False,
                'message': 'Unauthorised Access'
            })
            response.status_code = 403
            return response
