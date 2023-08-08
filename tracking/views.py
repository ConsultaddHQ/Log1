from django.db.models import F
from rest_framework.mixins import *
from django.db.models.functions import Lower
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from log1.utils import write_exception, ERROR_MSG, get_page_limits

from employee.models import User
from tracking.models import Devices, Location
from tracking.serializers import TrackingSerializer, TrackingDetailSerializer
from tracking.utils import get_address_by_location, string_to_decimal_point_converter


class TrackingViewSets(GenericViewSet, RetrieveModelMixin):
    queryset = User.objects.all()
    serializer_class = TrackingSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    # def retrieve(self, request, *args, **kwargs):
    #     try:
    #         user = get_object_or_404(User, id=kwargs.get('pk'))
    #         serializer = TrackingDetailSerializer(user)
    #         return Response({"data": serializer.data}, status=200)
    #     except Exception as error:
    #         write_exception(error, request)
    #         return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    def list(self, request, *args, **kwargs):
        first, last = get_page_limits(request)
        try:
            query = request.GET.get('query', None)
            users = User.objects.exclude(role__name='consultant').exclude(account_login=False)
            if query:
                users = users.filter(employee_name__istartswith=query)

            users = users.annotate(name=F('employee_name')).order_by(Lower('name'))
            serializer_data = self.serializer_class(users, many=True).data
            serializer_data.sort(key=lambda x: -x['active_login'])

            return Response({"data": serializer_data[first: last], "total": len(serializer_data)}, status=200)
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
                latitude = string_to_decimal_point_converter(latitude)
                longitude = string_to_decimal_point_converter(longitude)
                location_data = Location.objects.filter(latitude=latitude,longitude=longitude).first()
                if location_data:
                    Location.objects.create(
                        latitude=latitude,
                        longitude=longitude,
                        place_name=location_data.place_name,
                        state=location_data.state,
                        country=location_data.country,
                        pin_code=location_data.pin_code,
                        display_name=location_data.display_name,
                        device=devices_cookies
                    )
                else:
                    location_data = get_address_by_location(latitude, longitude)
                    if location_data:
                        Location.objects.create(
                            latitude=latitude,
                            longitude=longitude,
                            place_name=location_data["address"]["town"] if 'town' in location_data["address"] else location_data["address"]['city'] ,
                            state=location_data["address"]["state"],
                            country=location_data["address"]["country"],
                            pin_code=location_data["address"]["postcode"],
                            display_name = location_data["display_name"],
                            device=devices_cookies
                        )
                return Response({"data":"location added"}, status=201)
            return Response(
                {"message": "latitude or longitude not proper", "error": "latitude or longitude not proper"},
                status=400
            )
        except Exception as error:
            write_exception(message=error)
            return Response({"message": "Unable to fetch location", "error": str(error)}, status=400)

    @action(methods=['GET'], detail=True, url_path='get_locations')
    def get_device_locations(self, request, *args, **kwargs):
        try:
            device = get_object_or_404(Devices, id=kwargs.get('pk'))
            location_data = device.location.all().values(
                'display_name', 'modified'
            )
            return Response({"data": location_data}, status=200)
        except Exception as error:
            write_exception(error, request)
            return Response({"message": ERROR_MSG, "error": str(error)}, status=400)

    # @action(methods=['GET'], detail=True, url_path='get_export_info')
    # def get_device_export(self, request, *args, **kwargs):
    #     try:
    #         data = {}
    #         device = get_object_or_404(Devices, id=kwargs.get('pk'))
    #         export_dates = set(device.export_data.all().values('created'))
    #         for date in export_dates:
    #             exported_items = device.export_data.filter(created=data)
    #             data =
    #         return Response({"data": location_data}, status=200)
    #     except Exception as error:
    #         write_exception(error, request)
    #         return Response({"message": ERROR_MSG, "error": str(error)}, status=400)
