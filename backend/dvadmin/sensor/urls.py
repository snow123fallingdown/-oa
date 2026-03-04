from rest_framework import routers
from .views import SensorDeviceViewSet, SensorLogViewSet

from django.urls import path
router = routers.SimpleRouter()
# router.register(r'device', SensorDeviceViewSet)
router.register(r'device', SensorDeviceViewSet)
router.register(r'log', SensorLogViewSet)



urlpatterns = [
    
]
urlpatterns += router.urls