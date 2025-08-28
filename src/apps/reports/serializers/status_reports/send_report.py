from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report


class ReportSendSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    status = serializers.CharField(read_only=True)
    sent_at = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ["id", "status", "sent_at"]

    def validate(self, attrs):
        instance: Report = self.instance
        if instance.status != Report.StatusChoices.SAVED:
            raise CustomExceptionError(code=400, detail=_("Report must be in SAVED state to be sent."))
        return attrs

    def save(self, **kwargs):
        instance: Report = self.instance
        user = self.context["request"].user

        # 1. Asl reportni yuborish
        instance.status = Report.StatusChoices.SENT
        if not instance.sent_at:
            instance.sent_at = timezone.now()
        instance.sent_by = user
        instance.sent_by_org = getattr(user, "organization", None)
        instance.sent_by_role = getattr(user, "role", None)
        instance.save(update_fields=["status", "sent_at", "sent_by", "sent_by_org", "sent_by_role"])

        # 2. Tegishli viloyat jami (regional general) ham agar mavjud bo‘lsa va SAVED bo‘lsa SENT qilinadi
        if instance.organization and instance.statement and instance.deadline:
            regional_general = Report.objects.filter(
                organization=None,
                is_general=True,
                region=instance.organization.region,
                statement=instance.statement,
                deadline=instance.deadline
            ).first()
            if regional_general and regional_general.status == Report.StatusChoices.SAVED:
                regional_general.status = Report.StatusChoices.SENT
                if not regional_general.sent_at:
                    regional_general.sent_at = timezone.now()
                regional_general.save(update_fields=["status", "sent_at"])

        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.sent_at:
            rep["sent_at"] = instance.sent_at.strftime("%Y-%m-%d %H:%M")
        else:
            rep["sent_at"] = None
        return rep
