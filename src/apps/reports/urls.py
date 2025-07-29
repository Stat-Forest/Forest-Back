from django.urls import path

from apps.reports.views import (
    DeadlineListAPIView, ReportListAPIView, ReportSendAPIView,
    ReportCancelAPIView, ReportAcceptAPIView,
    ReportCreateAPIView, StatementListAPIView,
    ReportItemListAPIView, DashboardStatListView,
    StatementColumnTreeAPIView, UserListAPIView,
    ReportUpdateAPIView, ReportRetrieveAPIView, ReportDeleteAPIView,
    PlanStatementColumnListAPIView, PlanCreateView,
    PlanListAPIView,PlanDeleteAPIView,PlanItemBulkUpdateView
)
from apps.reports.views.column_plant import ColumnPlantListAPIView

from apps.reports.views.plant_column import PlantListAPIView
from apps.reports.views.plant_report import KochatReportListAPIView, NiXolReportListAPIView

urlpatterns = [

    # ====================  USERS URL   ====================
    path('users/', UserListAPIView.as_view(), name='users'),

    # ====================  DASHBOARD URL   ====================
    path('dashboard/', DashboardStatListView.as_view(), name='dashboard'),

    # ====================  DEADLINE URL    ====================
    path('deadlines/', DeadlineListAPIView.as_view(), name='deadline-list'),

    # ====================  STATEMENT COLUMN URL    ====================
    path('statements/', StatementListAPIView.as_view(), name='report-list'),
    path('statement-columns/', StatementColumnTreeAPIView.as_view(), name='statement-columns-list'),

    # ====================  REPORT URL    ====================
    path('', ReportListAPIView.as_view(), name='report-list'),
    path('create/', ReportCreateAPIView.as_view(), name='report-create'),
    path('<uuid:id>/', ReportRetrieveAPIView.as_view(), name='report-detail'),
    path('<uuid:id>/update/', ReportUpdateAPIView.as_view(), name='report-update'),
    path('<uuid:id>/delete/', ReportDeleteAPIView.as_view(), name='report-delete'),

    # ====================  REPORT STATUS URL    ====================
    path('send/', ReportSendAPIView.as_view(), name='report-send'),
    path('cancel/', ReportCancelAPIView.as_view(), name='report-cancel'),
    path('accept/', ReportAcceptAPIView.as_view(), name='report-accept'),


    # ====================  REPORT ITEM URL    ====================
    path('report-items/', ReportItemListAPIView.as_view(), name='report-item-list'),


    # ====================  PLAN URL    ====================
    path('plan-columns/', PlanStatementColumnListAPIView.as_view(), name='plane-columns-list'),
    path('plan-list/', PlanListAPIView.as_view(), name='plan-create'),
    path('plan-create/', PlanCreateView.as_view(), name='plan-create'),
    path('plans/<uuid:pk>/delete/', PlanDeleteAPIView.as_view(), name='plan-delete'),
    path("plans/<uuid:pk>/update-values/", PlanItemBulkUpdateView.as_view(), name="planitem-bulk-update"),


    # ====================  PLANT URL FOR SPECIALLY    ====================
    path("plants/", PlantListAPIView.as_view(), name="plant-list"),
    path("plant-report/kochat/", KochatReportListAPIView.as_view(), name="plant-report-kochat-list"),
    path("plant-report/nihol/", NiXolReportListAPIView.as_view(), name="plant-report-nixol-list"),
    path("column-plants/", ColumnPlantListAPIView.as_view(), name="column-plant-lists")
]
