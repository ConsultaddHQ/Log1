from django.db.models import F
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from tracking.models import Devices, Location, ExportData
from employee.models import User


class TrackingSerializer(serializers.ModelSerializer):
    active_login = serializers.SerializerMethodField()
    export_click = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'employee_id', 'email', 'employee_name', 'active_login', 'export_click')

    @staticmethod
    def get_export_click(obj):
        devices = obj.devices.all()
        all_count = 0
        for device in devices:
            all_count += len(device.export_data.all())
        return all_count
    
    @staticmethod
    def get_active_login(obj):
        login_count = len(obj.devices.all())
        return login_count
    
    
class TrackingDetailSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    export_data = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'employee_id', 'employee_name','location', 'export_data')

    @staticmethod
    def get_location(obj):
        devices = obj.devices.all()
        locations = []
        for device in devices:
            device_location = device.location.all().first()
            if device_location:
                locations.append({
                    "device_id": device.device_id,
                    "state": device_location.state,
                    "country": device_location.country,
                    "place": device_location.place_name,
                    "pin_code": device_location.pin_code,
                    "display_name": device_location.display_name,
                })
        return locations

    @staticmethod
    def get_export_data(obj):
        devices = obj.devices.all()
        result_data = {}
        data = []
        for device in devices:
            export_datas = device.export_data.all()
            if len(export_datas) > 0:
                for _data in export_datas:
                    key = _data.name
                    result_data[key] = result_data.get(key, 0) + 1
                    
        for key, value in result_data.items():
            data.append({
                "type": key,
                "count": value,
            })
        return data
    