# pyrefly: ignore [missing-import]
from django.urls import path

from apps.reports.views import (
    ReportListAPIView,
    ReportCreateAPIView, ReportItemListAPIView,
    ReportUpdateAPIView, ReportRetrieveAPIView, ReportDeleteAPIView,

)
from apps.reports.views.filtered_general import FilteredGeneralReportAPIView
from apps.reports.views.column_plant import ColumnPlantListAPIView
from apps.reports.views.exports.export_excel import ReportExcelExportAPIView, ReportExcelDownloadAPIView
from apps.reports.views.list_reports import IndividualGeneralReport, IndividualGeneralReportDetail, \
    RegionalGeneralReport, RegionalGeneralReportDetail, RepublicGeneralReport, RepublicGeneralReportDetail

from apps.reports.views.plan import (
    PlanCreateView,
    PlanListAPIView,
    PlanDeleteAPIView,
    PlanUpdateView,
    PlanRetrieveView,
    PlanStatementColumnListAPIView,
    PlanItemDetailAPIView
)

from apps.reports.views.deadline import (
    DeadlineListAPIView,
    DeadlineExpiredListAPIView,
    DeadlineLoginStatListAPIView
)
from apps.reports.views.dashboard import (
    DashboardOverviewAPIView,
    DashboardStatListView,
)
from apps.reports.views.plant_report import PlantListReportAPIView, UniversalPlantReportCreateAPIView, \
    PlantDetailReportAPIView, PlantUpdateReportAPIView, PlantReportDeleteAPIView
from apps.reports.views.plant_svodka import PlantSvodkaAPIView
from apps.reports.views.source_view import AcceptedKochatNiholSourceReportsAPIView

from apps.reports.views.statement.statement import StatementListAPIView

from apps.reports.views.statement.statement_column import StatementColumnTreeAPIView

from apps.reports.views.statement.statement_column_corrected_org_name import CorrectedStatementColumnTreeAPIView
from apps.reports.views.statement.appendices import StatementAppendicesAPIView

from apps.reports.views.users import (
    UserListAPIView,
)

from apps.reports.views.status_reports import (
    ReportSignChallengeAPIView,
    ReportSignatureVerifyAPIView,
    ReportSendAPIView,
    ReportCancelAPIView,
    ReportAcceptAPIView,
)

from apps.reports.views.select_report import ReportAggregateSelectedAPIView

from apps.reports.views.plant_column import PlantListAPIView

from apps.report_admin_stat.views import StatementReportStatView



from apps.reports.views.plan_excel import (
    PlanExcelTemplateAPIView,
    PlanExcelImportAPIView,
    PlanExcelExportAPIView,
)

from apps.reports.views.imports.import_excel import (
    ImportTemplateDownloadAPIView,
    ImportParseAPIView,
)


urlpatterns = [

    # ====================  USERS URL   ====================
    path('users/', UserListAPIView.as_view(), name='users'),

    # ====================  DASHBOARD URL   ====================
    path('dashboard/', DashboardStatListView.as_view(), name='dashboard'),
    path('dashboard/statement-stats/', StatementReportStatView.as_view(), name='statement-stats'),
    path('dashboard/overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),


    # ====================  DEADLINE URL    ====================
    path('deadlines/', DeadlineListAPIView.as_view(), name='deadline-list'),
    path('expired-deadlines/', DeadlineExpiredListAPIView.as_view(), name='expired-deadlines'),
    path('login-stat-deadlines/', DeadlineLoginStatListAPIView.as_view(), name='login-deadlines'),

    # ====================  STATEMENT COLUMN URL    ====================
    path('statements/', StatementListAPIView.as_view(), name='report-list'),
    path('statement-columns/', StatementColumnTreeAPIView.as_view(), name='statement-columns-list'),
    path('statement-columns-corrected-org-name/', CorrectedStatementColumnTreeAPIView.as_view(),
         name='statement-columns-corrected-org-name-list'),
    path('statement-appendices/', StatementAppendicesAPIView.as_view(), name='statement-appendices'),

    # ====================  REPORT URL    ====================
    path('', ReportListAPIView.as_view(), name='report-list'),
    path('filtered-general/', FilteredGeneralReportAPIView.as_view(), name='filtered-general'),
    path('create/', ReportCreateAPIView.as_view(), name='report-create'),
    path('<uuid:id>/', ReportRetrieveAPIView.as_view(), name='report-detail'),
    path('<uuid:id>/update/', ReportUpdateAPIView.as_view(), name='report-update'),
    path('<uuid:id>/delete/', ReportDeleteAPIView.as_view(), name='report-delete'),

    # ====================  REPORT URL    ====================
    path("aggregate/", ReportAggregateSelectedAPIView.as_view(), name="report-aggregate"),

    # ====================  REPORT STATUS URL    ====================
    path('send/', ReportSendAPIView.as_view(), name='report-send'),
    path('send/challenge/', ReportSignChallengeAPIView.as_view(), name='report-send-challenge'),
    path('signatures/<uuid:signature_id>/verify/', ReportSignatureVerifyAPIView.as_view(), name='report-signature-verify'),
    path('cancel/', ReportCancelAPIView.as_view(), name='report-cancel'),
    path('accept/', ReportAcceptAPIView.as_view(), name='report-accept'),

    # INDIVIDUAL GENERAL REPORTS
    path("individual/", IndividualGeneralReport.as_view(), name="individual-general-list"),
    path("individual/<uuid:pk>/", IndividualGeneralReportDetail.as_view(), name="individual-general-detail"),

    # REGIONAL GENERAL REPORTS
    path("regional/", RegionalGeneralReport.as_view(), name="regional-general-list"),
    path("regional/<uuid:pk>/", RegionalGeneralReportDetail.as_view(), name="regional-general-detail"),

    # REPUBLIC GENERAL REPORTS
    path("republic/", RepublicGeneralReport.as_view(), name="republic-general-list"),
    path("republic/<uuid:pk>/", RepublicGeneralReportDetail.as_view(), name="republic-general-detail"),

    # ====================  REPORT ITEM URL    ====================
    path('report-items/', ReportItemListAPIView.as_view(), name='report-item-list'),

    # ====================  PLAN URL    ====================
    path('plan-columns/', PlanStatementColumnListAPIView.as_view(), name='plane-columns-list'),
    path('plan-list/', PlanListAPIView.as_view(), name='plan-create'),
    path('plan-create/', PlanCreateView.as_view(), name='plan-create'),
    path("plan/<uuid:pk>/update/", PlanUpdateView.as_view(), name="plan-update"),
    path("plan/<uuid:pk>/", PlanRetrieveView.as_view(), name="plan-detail"),
    path('plans/<uuid:pk>/delete/', PlanDeleteAPIView.as_view(), name='plan-delete'),
    path("plan-items/", PlanItemDetailAPIView.as_view(), name="planitem-detail"),

    path("plan-excel/template/", PlanExcelTemplateAPIView.as_view(), name="plan-excel-template"),
    
    path("plan-excel/import/", PlanExcelImportAPIView.as_view(), name="plan-excel-import"),
    path("plan-excel/export/", PlanExcelExportAPIView.as_view(), name="plan-excel-export"),

    # ====================  JADVAL IMPORT URL ====================
    path("import-template/", ImportTemplateDownloadAPIView.as_view(), name="import-excel-template"),
    path("import-parse/", ImportParseAPIView.as_view(), name="import-excel-parse"),


    # ====================  PLANT URL FOR SPECIALLY    ====================
    path("plants/", PlantListAPIView.as_view(), name="plant-list"),
    path("column-plants/", ColumnPlantListAPIView.as_view(), name="column-plant-lists"),

    path("plant/create/", UniversalPlantReportCreateAPIView.as_view(), name="plant-create"),
    path("report-plant/<uuid:pk>/update", PlantUpdateReportAPIView.as_view(), name="plant-update"),
    path("report-plant/", PlantListReportAPIView.as_view(), name="plant-by-app"),
    path("report-plant/<uuid:pk>/", PlantDetailReportAPIView.as_view(), name="plant-by-app"),
    path("report-plant/<uuid:pk>/delete", PlantReportDeleteAPIView.as_view(), name="plant-delete"),

    # ====================  PLANT SVODKA (Calculated) =================
    path("plant-svodka/", PlantSvodkaAPIView.as_view(), name="plant-svodka"),

    # ====================  EXPORT URL =================
    path("export-excel/", ReportExcelExportAPIView.as_view(), name="export-excel"),
    path("export-excel/download/", ReportExcelDownloadAPIView.as_view(), name="export-excel-download"),

    # ====================  SOURCE SVODKA ========================
    path("source-reports/kochat-nihol/", AcceptedKochatNiholSourceReportsAPIView.as_view(),
         name="accepted-kochat-nihol-sources",
    ),
]
