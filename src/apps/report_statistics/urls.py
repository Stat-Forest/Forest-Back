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
    StatisticsRentLandAPIView,
    StatisticsCoveredLandAPIView
)


from apps.report_statistics.views.establishment_forest import (
    StatisticsClosedRootAPIView,
    StatisticsBuildForestAPIView
)

urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('finance-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    # path('finance-income-stat/',StatisticsFinanceIncomeAPIView.as_view()),
    # path('land-acquisition-stat/',StatisticsLandAcquisitionAPIView.as_view()),
    # path('land-rented-stat/',StatisticsRentLandAPIView.as_view()),
    # path('land-covered-stat/',StatisticsCoveredLandAPIView.as_view()),
    # path('closed-forest-stat/',StatisticsClosedRootAPIView.as_view()),
    # path('build-forest-stat/',StatisticsBuildForestAPIView.as_view()),
]