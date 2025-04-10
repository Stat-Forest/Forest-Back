from django.urls.conf import path

from src.apps.reports.views.report import ReportListAPIView

urlpatterns = [
    path('',ReportListAPIView.as_view()),
]