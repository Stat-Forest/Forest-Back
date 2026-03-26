# urls.py

from django.urls import path
from .views import StatementReportExportView

urlpatterns = [
    path('stats/export/', StatementReportExportView.as_view(), name='statement-stats-export'),
]