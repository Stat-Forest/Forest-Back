from django.urls import path
from apps.report_statistics.views import (
    StatisticsEmployeeReportAPIView,
    StatisticsEmployeeReportAnalysisAPIView,
    StatisticsFinanceFundAPIView,
    StatisticsFinanceIncomeAPIView
)


urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('employee-analysis-stat/',StatisticsEmployeeReportAnalysisAPIView.as_view()),
    path('employee-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    path('rdsdsververv/',StatisticsFinanceIncomeAPIView.as_view()),
]