from django.urls import path

from apps.information_analytical.views.forest_monitoring import ForestMonitoringAPIView

urlpatterns = [
    path("", ForestMonitoringAPIView.as_view(), name="forest_monitoring"),
]