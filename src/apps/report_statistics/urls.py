from django.urls import path

from apps.report_statistics.views.employee import (
    StatisticsEmployeeReportAPIView,
    StatisticsEmployeeReportAnalysisAPIView,
)
from apps.report_statistics.views.finance import (
    StatisticsFinanceFundAPIView,
    StatisticsFinanceIncomeAPIView,
)
from apps.report_statistics.views.land_management import (
    StatisticsLandAcquisitionAPIView,
    StatisticsRentedLandAPIView,
    StatisticsLandAcquisitionAPIView
)


urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('employee-analysis-stat/',StatisticsEmployeeReportAnalysisAPIView.as_view()),
    path('finance-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    path('finance-income-stat/',StatisticsFinanceIncomeAPIView.as_view()),
    path('land-acquisition-stat/',StatisticsLandAcquisitionAPIView.as_view()),
    path('land-rented-stat/',StatisticsRentedLandAPIView.as_view()),
    path('land-forest-stat/',StatisticsLandAcquisitionAPIView.as_view()),
]