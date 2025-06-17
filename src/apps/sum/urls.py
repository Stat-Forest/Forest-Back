from django.urls import path
from apps.sum.views import SumEmployeeReportListAPIView

urlpatterns =[
    path('employee_report/',SumEmployeeReportListAPIView.as_view(), name='employee-report')
]