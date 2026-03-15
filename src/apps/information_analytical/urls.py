from django.urls import path

from apps.information_analytical.views.forest_monitoring import ForestMonitoringAPIView
from apps.information_analytical.views.information_monitoring_export import ForestMonitoringExportAPIView


urlpatterns = [
    path("", ForestMonitoringAPIView.as_view(), name="forest_monitoring"),
    path(
        "export-excel/", ForestMonitoringExportAPIView.as_view(),
        name="forest-monitoring-export",
    ),
]
