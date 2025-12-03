from drf_spectacular.utils import extend_schema
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from apps.reports.permissions import CanCancelReport
from apps.reports.models import Report
from apps.reports.serializers.status_reports import ReportCancelSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Reports Status Update"])
class ReportCancelAPIView(DRFHistoryMixin,UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportCancelSerializer
    permission_classes = [CanCancelReport]

    def get_object(self):
        # Report ID body orqali olinadi
        report_id = self.request.data.get("id")
        if not report_id:
            raise CustomExceptionError(
                code=400,
                detail={"id": _("This field is required.")}
            )

        try:
            report = self.get_queryset().get(id=report_id)
        except Report.DoesNotExist:
            raise CustomExceptionError(
                code=404,
                detail={"report": _("Report not found.")}
            )

        self.check_object_permissions(self.request, report)
        return report

    def post(self, request, *args, **kwargs):
        # POST so‘rovni ham UpdateAPIView orqali ishlatish uchun
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
