from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.exceptions import ValidationError, NotFound

from apps.reports.models import Report
from apps.reports.permissions import CanSendReport
from apps.reports.permissions.report_scope import ReportScopedQuerysetMixin
from apps.reports.serializers.status_reports import ReportSendSerializer
from apps.reports.services.report_signing import build_signing_challenge
from apps.logs.drf_mixins import DRFHistoryMixin
from rest_framework.response import Response


class _ReportByIdMixin:
    """Body'dagi `id` bo'yicha hisobotni (foydalanuvchi doirasida) topadi."""

    def get_object(self):
        report_id = self.request.data.get("id")
        if not report_id:
            raise ValidationError({"id": "This field is required."})
        try:
            obj = self.get_queryset().get(id=report_id)
        except Report.DoesNotExist:
            raise NotFound("Report not found.")
        self.check_object_permissions(self.request, obj)
        return obj



@extend_schema(tags=["Reports Status Update"])
class ReportSignChallengeAPIView(_ReportByIdMixin, ReportScopedQuerysetMixin, GenericAPIView):
    """
    Yuborishdan oldin imzolanadigan hujjat matnini beradi. Frontend uni
    E-imzo bilan imzolab, pkcs7 ni /reports/send/ ga yuboradi.
    Ruxsatlar yuborish bilan bir xil (faqat tashkilot rahbari, saved holat).
    """
    queryset = Report.objects.all()
    serializer_class = ReportSendSerializer
    permission_classes = [CanSendReport]

    def post(self, request, *args, **kwargs):
        report = self.get_object()
        return Response(build_signing_challenge(report, request.user, request))


@extend_schema(tags=["Reports Status Update"])
class ReportSendAPIView(DRFHistoryMixin, _ReportByIdMixin, ReportScopedQuerysetMixin, UpdateModelMixin, GenericAPIView):
    """Hisobotni yuborish. Majburiy E-imzo imzosi (`pkcs7`) bilan."""
    queryset = Report.objects.all()
    serializer_class = ReportSendSerializer
    permission_classes = [CanSendReport]

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)