from django.urls import path
from apps.sum.views import (
    SumEmployeeReportListAPIView,
    SumEmployeeReportAnalysisListAPIView,
    SumFundIncomeAnalysisListAPIView,
    SumFundAnalysisListAPIView,
    SumAcquisitionLandAnalysisListAPIView,
    SumRentedAnalysisListAPIView,
    SumCoveredForestLandAnalysisListAPIView
)

urlpatterns = [
    path('employee-report/', SumEmployeeReportListAPIView.as_view(), name='employee-report'),
    path('employee-analysis/', SumEmployeeReportAnalysisListAPIView.as_view(), name='employee-analysis'),
    path('finance-income/', SumFundIncomeAnalysisListAPIView.as_view(), name='finance-income'),
    path('finance-fund/', SumFundAnalysisListAPIView.as_view(), name='finance-income'),
    path('land-acquisition/', SumAcquisitionLandAnalysisListAPIView.as_view(), name='land-acquisition'),
    path('land-rented/', SumRentedAnalysisListAPIView.as_view(), name='land-rented'),
    path('land-covered-forest/', SumCoveredForestLandAnalysisListAPIView.as_view(), name='land-covered-forest')
]
