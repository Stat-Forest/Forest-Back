from django.urls import path
from apps.reports.views import DeadlineListView, ReportListAPIView, ReportCreateAPIView, ReportDetailAPIView, \
    ReportStatusUpdateAPIView, ReportItemListView, ReportItemDetailView
from apps.reports.views import DashboardStatListView
from apps.reports.views import StatementColumnListAPIView

urlpatterns = [
    path('dashboard/', DashboardStatListView.as_view(), name='dashboard'),
    path('deadlines/', DeadlineListView.as_view(), name='deadline-list'),
    path('statement-columns/', StatementColumnListAPIView.as_view(), name='statement-columns-list'),
    path('', ReportListAPIView.as_view(), name='report-list'),
    path('create/', ReportCreateAPIView.as_view(), name='report-create'),
    path('<int:id>/', ReportDetailAPIView.as_view(), name='report-detail'),
    path('<int:id>/update-status/', ReportStatusUpdateAPIView.as_view(), name='report-status-update'),
    path('report-items/', ReportItemListView.as_view(), name='reportitem-list'),
    path('report-items/<int:pk>/', ReportItemDetailView.as_view(), name='reportitem-detail'),
]


