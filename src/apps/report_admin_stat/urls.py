# urls.py

from django.urls import path
from .views import StatementReportStatView, StatementReportExportView

urlpatterns = [
    path('dashboard/statement-stats/', StatementReportStatView.as_view(), name='statement-stats'),
    path('dashboard/stats/export/', StatementReportExportView.as_view(), name='statement-stats-export'),
]