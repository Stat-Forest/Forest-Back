from django.urls import path

from apps.reports.views import AllReportListAPIView, ReportListAPIView

urlpatterns = [
    path('', ReportListAPIView.as_view()),
    path('all/', AllReportListAPIView.as_view()),
]


