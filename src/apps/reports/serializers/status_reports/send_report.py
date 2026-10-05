from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.reports.services.report_signing import verify_and_store_signature


class ReportSendSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    # Rahbarning E-imzo imzosi: /reports/send/challenge/ bergan matnning
    # attached PKCS#7 (base64) ko'rinishi. Imzosiz yuborib bo'lmaydi.
    pkcs7 = serializers.CharField(write_only=True, required=True, allow_blank=False)
    # Challenge rejimida (VPN'siz) imzo hujjatni emas, e-imzo challenge'ni
    # o'z ichiga oladi — hisobot nonce orqali topiladi.
    nonce = serializers.CharField(write_only=True, required=False, allow_blank=True)
    status = serializers.CharField(read_only=True)
    sent_at = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ["id", "pkcs7", "nonce", "status", "sent_at"]

    def validate(self, attrs):
        instance: Report = self.instance

        # View partial_update ishlatadi, partial rejimda `required` tekshirilmaydi —
        # shuning uchun imzo borligini shu yerda majburlaymiz.
        if not (attrs.get("pkcs7") or "").strip():
            raise CustomExceptionError(
                code=400,
                detail=_("Hisobotni yuborish uchun E-imzo bilan imzolash shart (pkcs7).")
            )

        if DaromadQuarterService.is_daromad_report(instance):
            # Daromad uchun: current_quarter ning statusini tekshiramiz
            current_quarter = instance.current_quarter
            if not current_quarter:
                raise CustomExceptionError(
                    code=400,
                    detail=_("Daromad hisobotida joriy chorak aniqlanmagan.")
                )

            current_quarter_status = instance.get_quarter_status(current_quarter)
            if current_quarter_status != Report.StatusChoices.SAVED:
                raise CustomExceptionError(
                    code=400,
                    detail=_(
                        f"{DaromadQuarterService.get_quarter_display(current_quarter)} "
                        f"jo'natish uchun SAVED holatda bo'lishi kerak. "
                        f"Hozirgi holat: {current_quarter_status}"
                    )
                )
        else:
            # Oddiy report uchun: report.status tekshiramiz
            if instance.status != Report.StatusChoices.SAVED:
                raise CustomExceptionError(
                    code=400,
                    detail=_("Report must be in SAVED state to be sent.")
                )

        return attrs

    def save(self, **kwargs):
        # Imzo tekshiruvi va status o'zgarishi bitta tranzaksiyada: imzo
        # saqlanib, status yangilanmay qolishi (yoki aksi) mumkin emas.
        with transaction.atomic():
            return self._sign_and_send()

    def _sign_and_send(self):
        instance: Report = self.instance
        request = self.context["request"]
        user = request.user

        self._signature = verify_and_store_signature(
            report=instance,
            user=user,
            pkcs7=self.validated_data["pkcs7"],
            request=request,
            nonce=self.validated_data.get("nonce") or "",
        )

        instance.sent_by = user
        instance.sent_by_org = getattr(user, "organization", None)
        instance.sent_by_role = getattr(user, "role", None)

        update_fields = ["sent_by", "sent_by_org", "sent_by_role"]

        if DaromadQuarterService.is_daromad_report(instance) and instance.current_quarter:
            # Daromad: faqat current_quarter statusini SENT qilamiz
            # report.status = compute_report_status() — Q1 ACCEPTED bo'lsa ACCEPTED qoladi
            status_field = DaromadQuarterService.get_quarter_status_field(instance.current_quarter)
            setattr(instance, status_field, Report.StatusChoices.SENT)
            DaromadQuarterService.mark_quarter_sent(instance, instance.current_quarter)

            # sent_at faqat birinchi marta yoziladi
            if not instance.sent_at:
                instance.sent_at = timezone.now()
                update_fields.append("sent_at")

            # report.status ni qayta hisoblaymiz
            instance.status = DaromadQuarterService.compute_report_status(instance)
            update_fields.extend([status_field, "quarter_status_dates", "status"])
        else:
            # Oddiy report
            instance.status = Report.StatusChoices.SENT
            if not instance.sent_at:
                instance.sent_at = timezone.now()
            update_fields.extend(["status", "sent_at"])

        instance.save(update_fields=list(dict.fromkeys(update_fields)))

        # Eski logika: regional general report ham SAVED bo'lsa SENT qilinadi
        if instance.organization and instance.statement and instance.deadline:
            regional_general = Report.objects.filter(
                organization=None,
                is_general=True,
                region=instance.organization.region,
                statement=instance.statement,
                deadline=instance.deadline,
            ).first()
            if regional_general and regional_general.status == Report.StatusChoices.SAVED:
                regional_general.status = Report.StatusChoices.SENT
                if not regional_general.sent_at:
                    regional_general.sent_at = timezone.now()
                regional_general.save(update_fields=["status", "sent_at"])

        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["sent_at"] = instance.sent_at.strftime("%Y-%m-%d %H:%M") if instance.sent_at else None
        signature = getattr(self, "_signature", None)
        rep["signature_id"] = str(signature.id) if signature else None
        return rep
