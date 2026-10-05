from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, views
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.reports.models import ReportSignature
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.reports.services.report_signing import compute_items_hash
from apps.utils.translation import get_translated_field


def _mask_pinfl(pinfl: str) -> str:
    if not pinfl:
        return ""
    return "*" * max(len(pinfl) - 4, 0) + pinfl[-4:]


@extend_schema(tags=["Reports Status Update"], auth=[])
class ReportSignatureVerifyAPIView(views.APIView):
    """
    Ochiq sahifa: QR koddan ochiladi. Imzo kim tomonidan, qachon qo'yilgani,
    qaysi hisobotga tegishli ekani va hisobot imzodan keyin o'zgartirilmagani.
    Login talab qilinmaydi, shuning uchun shaxsiy ma'lumotlar qisqartirib beriladi.
    """
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (AnonRateThrottle,)

    def get(self, request, signature_id):
        signature = get_object_or_404(
            ReportSignature.objects.select_related(
                "report", "report__organization", "report__statement", "report__deadline",
            ),
            id=signature_id,
        )
        report = signature.report
        lang = (request.query_params.get("lang") or "uz").lower()
        if lang not in ("uz", "ru"):
            lang = "uz"

        if signature.quarter and DaromadQuarterService.is_daromad_report(report):
            report_status = report.get_quarter_status(signature.quarter)
        else:
            report_status = report.status

        unchanged = compute_items_hash(report) == signature.items_hash
        tst = (signature.verify_result.get("signers") or [{}])[0].get("timeStamp") or {}

        return Response({
            "id": str(signature.id),
            "valid": bool(signature.is_valid and signature.verify_status == 1),
            "report_unchanged": unchanged,
            "signed_at": signature.signed_at,
            "timestamped": bool(signature.verify_result.get("timestamped")),
            "timestamp_tsa": tst.get("tsa"),
            "signer": {
                "full_name": signature.signer_cn,
                "tin": signature.signer_tin,
                "pinfl_masked": _mask_pinfl(signature.signer_pinfl),
                "cert_serial": signature.cert_serial,
                "cert_valid_from": signature.cert_valid_from,
                "cert_valid_to": signature.cert_valid_to,
            },
            "report": {
                "id": str(report.id),
                "organization": get_translated_field(report.organization, "name", lang) if report.organization else None,
                "statement": get_translated_field(report.statement, "name", lang) if report.statement else None,
                "period": str(getattr(report.deadline, "submit_at", "") or ""),
                "quarter": signature.quarter,
                "status": report_status,
            },
            "document_hash": signature.document_hash,
        })
