from apps.reports.models import ReportItem, Report
from apps.reports.serializers import ReportItemSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.base.views import CustomListAPIView, CustomRetrieveUpdateAPIView


class ReportItemListView(CustomListAPIView):
    queryset = ReportItem.objects.select_related('report', 'department_column')
    serializer_class = ReportItemSerializer


class ReportItemDetailView(CustomRetrieveUpdateAPIView):
    queryset = ReportItem.objects.select_related('report')
    serializer_class = ReportItemSerializer

    def check_report_status(self, report_item):
        if report_item.report.status != Report.StatusChoices.NEW:
            raise CustomExceptionError(code=400, detail={
                "status": 'This report item can not be updated.'
            })

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_report_status(instance)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_report_status(instance)
        return super().destroy(request, *args, **kwargs)