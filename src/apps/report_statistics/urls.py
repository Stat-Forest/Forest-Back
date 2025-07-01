from django.urls import path
from apps.report_statistics.views import (
    StatisticsEmployeeReportAPIView,
    StatisticsEmployeeReportAnalysisAPIView,
    StatisticsFinanceFundAPIView,
    StatisticsFinanceIncomeAPIView,
    StatisticsLandAcquisitionAPIView,
    StatisticsRentedLandAPIView,
    StatisticsForestLandAPIView
)


urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('employee-analysis-stat/',StatisticsEmployeeReportAnalysisAPIView.as_view()),
    path('finance-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    path('finance-income-stat/',StatisticsFinanceIncomeAPIView.as_view()),
    path('land-acquisition-stat/',StatisticsLandAcquisitionAPIView.as_view()),
    path('land-rented-stat/',StatisticsRentedLandAPIView.as_view()),
    path('land-forest-stat/',StatisticsForestLandAPIView.as_view()),
]