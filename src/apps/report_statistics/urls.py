from django.urls import path

from apps.report_statistics.views.employee import (
    StatisticsEmployeeReportAPIView,
)
from apps.report_statistics.views.finance import (
    StatisticsFinanceFundAPIView,
)

from apps.report_statistics.views.build_forest import (
    StatisticsTerassaAPIView,
    StatisticsGolofitAPIView,
)

from apps.report_statistics.views.protect_forest import (
    StatisticsZararkunandaAPIView,
)

from apps.report_statistics.views.monitor_forest import (
    StatisticsYerOzlashtirishAmaldaAPIView,
)
from .views.login_statistiks import ReportLoginSummaryAPIView


urlpatterns =[
    path('employee-report-stat/',StatisticsEmployeeReportAPIView.as_view()),
    path('finance-fund-stat/',StatisticsFinanceFundAPIView.as_view()),
    path('build-forest-teressa/',StatisticsTerassaAPIView.as_view()),
    path('build-forest-golofit/',StatisticsGolofitAPIView.as_view()),
    path('protect-forest-zararkunanda/',StatisticsZararkunandaAPIView.as_view()),
    path('monitor-forest-uzlashtirish/',StatisticsYerOzlashtirishAmaldaAPIView.as_view()),

    #=========================== login stats ===============================
    path('login-stats/',ReportLoginSummaryAPIView.as_view()),

]