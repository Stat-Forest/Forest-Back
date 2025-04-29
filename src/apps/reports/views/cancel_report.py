from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response

from apps.reports.models import Report
from apps.reports.serializers import ReportCancelSerializer
from apps.base.exceptions.exception_files import CustomExceptionError

class ReportCancelAPIView(UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCancelSerializer
    http_method_names = ['post']

    def get_object(self):
        report_id = self.request.data.get('id')
        if not report_id:
            raise CustomExceptionError(
                code=400,
                detail={'id': ['This field is required.']}
            )
        try:
            report = self.get_queryset().get(id=report_id)
        except Report.DoesNotExist:
            raise CustomExceptionError(
                code=404,
                detail={'report': ['Report not found.']}
            )
        self.check_object_permissions(self.request, report)
        return report

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
