from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.generics import UpdateAPIView

from apps.reports.models import Report
from apps.reports.permissions import CanAcceptReport
from apps.reports.serializers import ReportAcceptSerializer
from apps.base.exceptions.exception_files import CustomExceptionError

from django.utils.translation import gettext_lazy as _


@extend_schema(tags=["Reports Status Update"])
class ReportAcceptAPIView(UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportAcceptSerializer

    permission_classes = [CanAcceptReport]

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
                detail={'report': _('Report not found.')}
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
