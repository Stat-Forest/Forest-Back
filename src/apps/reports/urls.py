from django.urls import path

from apps.reports.views import AllReportListAPIView, ReportListAPIView
from apps.reports.views.deadline import DeadlineListAPIView

urlpatterns = [
    path('', ReportListAPIView.as_view()),
    path('all/', AllReportListAPIView.as_view()),
    path('deadlines/', DeadlineListAPIView.as_view()),
]


