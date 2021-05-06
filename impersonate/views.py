import inspect
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, ListModelMixin

from employee.models import User
from log1.utils import write_exception
from employee.serializers import UserSerializerLogin


# Route - /impersonate/
class ImpersonateViewSets(GenericViewSet, ListModelMixin, CreateModelMixin):
    # check if user is a superuser and has rights to impersonate
    queryset = User.objects.all()
    serializer_class = UserSerializerLogin
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def create(self, request, *args, **kwargs):
        try:
            if request.user.is_superuser:
                employee_id = request.data['employee_id']
                # check if requested impersonated user exists
                user_exists = User.objects.filter(employee_id=employee_id)
                if user_exists:
                    user = user_exists.first()
                    serializer = self.serializer_class(user)
                    return Response({"data": serializer.data, "message": "User is impersonated"}, status=201)
                else:
                    return Response({"message": 'User not Exist'}, status=400)
            else:
                return Response({"message": 'Unauthorised Access'}, status=401)
        except Exception as error:
            write_exception(message=error, class_name=self.get_classname(), function_name=inspect.stack()[0][3])
            return Response({"message": {'success': False, 'message': str(error)}}, status=400)
