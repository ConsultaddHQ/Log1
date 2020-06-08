from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, ListModelMixin

from employee.models import User
from employee.serializers import UserSerializerLogin


class ImpersonateViewSets(GenericViewSet, ListModelMixin, CreateModelMixin):
    # check if user is a superuser and has rights to impersonate
    queryset = User.objects.all()
    serializer_class = UserSerializerLogin
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
                    serializer = self.serializer_class(user)
                    return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": {'message': 'User not Exist'}}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": {'message': 'Unauthorised Access'}}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as error:
            return Response({"error": {'success': False, 'message': str(error)}}, status=status.HTTP_400_BAD_REQUEST)