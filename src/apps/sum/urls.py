from django.urls import path
from apps.sum.views import (
    SumEmployeeReportListAPIView,
    SumEmployeeReportAnalysisListAPIView,
    SumFundIncomeAnalysisListAPIView
    )

urlpatterns =[
    path('employee_report/',SumEmployeeReportListAPIView.as_view(), name='employee-report'),
    path('employee_analysis/',SumEmployeeReportAnalysisListAPIView.as_view(), name='employee-analysis'),
    path('fund_income/',SumFundIncomeAnalysisListAPIView.as_view(), name='fund-income')
]