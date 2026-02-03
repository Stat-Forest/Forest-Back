from django.urls import path

from apps.info_analysis.views import ReportAnalysisDashboardView


urlpatterns = [
    path('info/', ReportAnalysisDashboardView.as_view(), name='info-anal-list'),
]
