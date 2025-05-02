from django.urls import path
from apps.reports.views import (
    DeadlineListAPIView, ReportListAPIView, ReportSendAPIView,
    ReportCancelAPIView, ReportAcceptAPIView,
    ReportCreateAPIView,StatementListAPIView,
    ReportItemListAPIView, DashboardStatListView,
    StatementColumnListAPIView,UserListAPIView,
    ReportRetrieveUpdateAPIView, ReportDeleteAPIView
)

urlpatterns = [

    # ====================  USERS URL   ====================
    path('users/', UserListAPIView.as_view(), name='users'),

    # ====================  DASHBOARD URL   ====================
    path('dashboard/', DashboardStatListView.as_view(), name='dashboard'),

    # ====================  DEADLINE URL    ====================
    path('deadlines/', DeadlineListAPIView.as_view(), name='deadline-list'),

    # ====================  STATEMENT COLUMN URL    ====================
    path('statements/', StatementListAPIView.as_view(), name='report-list'),
    path('statement-columns/', StatementColumnListAPIView.as_view(), name='statement-columns-list'),

    # ====================  REPORT URL    ====================
    path('', ReportListAPIView.as_view(), name='report-list'),
    path('create/', ReportCreateAPIView.as_view(), name='report-create'),
    path('<uuid:id>/', ReportRetrieveUpdateAPIView.as_view(), name='report-detail'),
    path('<uuid:id>/delete/', ReportDeleteAPIView.as_view(), name='report-delete'),

    # ====================  REPORT STATUS URL    ====================
    path('send/', ReportSendAPIView.as_view(), name='report-send'),
    path('cancel/', ReportCancelAPIView.as_view(), name='report-cancel'),
    path('accept/', ReportAcceptAPIView.as_view(), name='report-accept'),


    # ====================  REPORT ITEM URL    ====================
    path('report-items/', ReportItemListAPIView.as_view(), name='report-item-list'),

]



