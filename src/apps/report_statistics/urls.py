from django.urls import path

from apps.report_statistics.views.employee import (
    StatisticsEmployeeReportAPIView,
    # StatisticsEmployeeReportAnalysisAPIView,
)
from apps.report_statistics.views.finance import (
    StatisticsFinanceFundAPIView,
    # StatisticsFinanceIncomeAPIView,
)

from apps.report_statistics.views.build_forest import (
    StatisticsTerassaAPIView,
    StatisticsGolofitAPIView,
)

from apps.report_statistics.views.protect_forest import (
    StatisticsZararkunandaAPIView,
)

from apps.report_statistics.views.land_management import (
    StatisticsLandAcquisitionAPIView,
    StatisticsRentLandAPIView,
    StatisticsCoveredLandAPIView
)


from apps.report_statistics.views.establishment_forest import (
    StatisticsClosedRootAPIView,
    # StatisticsBuildForestAPIView
)

urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('finance-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    path('build-forest-teressa/',StatisticsTerassaAPIView.as_view()),
    path('build-forest-golofit/',StatisticsGolofitAPIView.as_view()),
    path('protect-forest-zararkunanda/',StatisticsZararkunandaAPIView.as_view()),
    # path('land-covered-stat/',StatisticsCoveredLandAPIView.as_view()),
    # path('closed-forest-stat/',StatisticsClosedRootAPIView.as_view()),
    # path('build-forest-stat/',StatisticsBuildForestAPIView.as_view()),
]