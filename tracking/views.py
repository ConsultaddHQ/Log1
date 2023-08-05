from rest_framework.mixins import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import GenericViewSet
from django.db.models import F
from django.db.models.functions import Lower
from log1.utils import write_exception, write_info, DONT_HAVE_ACCESS, ERROR_MSG, get_page_limits
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from tracking.models import Devices, Location, ExportData
from employee.models import User
from tracking.serializers import TrackingSerializer, TrackingDetailSerializer
from tracking.utils import get_address_by_location

class TrackingViewSets(GenericViewSet):
    queryset = User.objects.all()
    serializer_class = TrackingSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def retrieve(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs.get('pk'))
            serializer = TrackingDetailSerializer(user)
            return Response({"data": serializer.data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        try:
            query = request.GET.get('query', '')
            users = User.objects.exclude(role__name='consultant').exclude(account_login=False)
            users = users.filter(employee_name__istartswith=query)
            users = users.annotate(name=F('employee_name')).order_by(Lower('name'))
            first, last = 0, len(users)
            serializer_data = self.serializer_class(users[first:last], many=True).data
            serializer_data.sort(key=lambda x: -x['active_login'])
                                 
            return Response({"data": serializer_data[0:10]}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
        

    @action(methods=['post'], detail=False, url_path='set_location')
    def set_location(self, request):
        try:
            # need to check if cookies id is available or not
            longitude = request.data.get('longitude', None)
            latitude = request.data.get('latitude', None)
            cookie_value = request.META.get('HTTP_X_ID_TOKEN', None) 
            devices_cookies = Devices.objects.filter(cookies_value=cookie_value).first()
            # ip address and location needs to determine here
            if latitude and longitude:
                location_data = get_address_by_location(latitude, longitude)
                if location_data:
                    location = Location.objects.create(
                        place_name=location_data["address"]["town"],
                        state=location_data["address"]["state"],
                        country=location_data["address"]["country"],
                        pin_code=location_data["address"]["postcode"],
                        device=devices_cookies
                    )
                return Response({"cookie":devices_cookies.cookies_value}, status=201)
            return Response({"message": "latitude or longitude not propper", "error": "latitude or longitude not propper"}, status=400)
        except Exception as error:
            write_exception(message=error)
            return Response({"message": "Unable to fatch location", "error": str(error)}, status=400)


