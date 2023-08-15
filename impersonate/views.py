from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, ListModelMixin

from impersonate.swagger import create_impersonate, impersonate_users
from log1.utils import write_exception
from employee.models import User, Handover
from employee.serializers import Token, UserSerializerLogin, HandoverSerializer, HandoverUserSerializer


# Route - /impersonate/
class ImpersonateViewSets(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializerLogin
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    @create_impersonate
    def create(self, request, *args, **kwargs):
        try:
            user_id = request.data.get('id')
            if not User.objects.filter(id=user_id).exists():
                return Response({"message": "User does not exist"}, status=404)

            if request.user.is_superuser:
                token, created = Token.objects.get_or_create(user_id=user_id)
                return Response({"data": {"token": token.key}, "message": "User is impersonated"}, status=201)
            else:
                handovers = Handover.objects.filter(handover_to=request.user)
                if handovers.filter(user_id=user_id).exists():
                    token, created = Token.objects.get_or_create(user_id=user_id)
                    return Response({"data": {"token": token.key}, "message": "User is impersonated"}, status=201)
                else:
                    return Response({"message": "You don't have permission to impersonate this User"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": {'success': False, 'message': str(error)}}, status=400)

    @impersonate_users
    @action(methods=['get'], detail=False, url_path='users')
    def users(self, request):
        try:
            if request.user.is_superuser:
                users = User.objects.exclude(role__name='consultant').exclude(is_active=False)
                serializer = HandoverUserSerializer(users, many=True)
            else:
                handovers = Handover.objects.filter(handover_to=request.user)
                serializer = HandoverSerializer(handovers, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)
