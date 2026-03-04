from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer
from .models import SensorDevice, SensorLog

class SensorDeviceSerializer(CustomModelSerializer):
    class Meta:
        model = SensorDevice
        fields = "__all__"

class SensorLogSerializer(CustomModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_location = serializers.CharField(source='device.location', read_only=True)

    class Meta:
        model = SensorLog
        fields = "__all__"