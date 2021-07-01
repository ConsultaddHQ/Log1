from django.db.models import F
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, ListModelMixin

from log1.utils import write_exception
from employee.models import User, Handover
from employee.serializers import Token, UserSerializerLogin, HandoverSerializer


# Route - /impersonate/
class ImpersonateViewSets(GenericViewSet, ListModelMixin, CreateModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializerLogin
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def list(self, request, *args, **kwargs):
        try:
            query = request.query_params.get('query', None)
            users = User.objects.exclude(role__name='consultant')
            if query:
                query = query.lstrip().replace(':amp:', '&')
                users = users.filter(employee_name__istartswith=query)
            data = users.annotate(name=F('employee_name')).order_by(Lower('name'))[:10].values(
                'id', 'employee_id', 'email', 'name'
            )
            return Response({"data": data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    def create(self, request, *args, **kwargs):
        try:
            user_id = request.data.get('id')
            get_object_or_404(User, id=user_id)
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

    @action(methods=['get'], detail=False, url_path='users')
    def users(self, request, *args, **kwargs):
        try:
            handovers = Handover.objects.filter(handover_to=request.user)
            serializer = HandoverSerializer(handovers, many=True)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)

    @action(methods=['post', 'delete'], detail=False, url_path='handover')
    def handover(self, request):
        try:
            if 'superadmin' in request.user.roles:
                user = get_object_or_404(User, id=request.data.get('user_id'))
                if request.method == 'POST':
                    handover_to = get_object_or_404(User, id=request.data.get('handover_id'))
                    handover, created = Handover.objects.get_or_create(user=user)
                    handover_to_name = handover.handover_to.employee_name
                    if created:
                        handover.handover_to = handover_to
                        handover.save()
                    else:
                        return Response({"message": f"User already assigned to {handover_to_name}"}, status=201)
                    return Response({"message": f"User handed over to {handover_to_name}"}, status=201)
                else:
                    handovers = Handover.objects.filter(user=user)
                    if handovers:
                        handovers.delete()
                        return Response({"message": f"User removed from Handover"}, status=201)
                    else:
                        return Response({"message": "User not found"}, status=404)
            else:
                return Response({"message": "You don't have permission to Handover"}, status=403)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": str(error)}, status=400)
