from rest_framework import serializers

from apps.reports.models import Report
from apps.base.serializers import CustomSerializer


class PlantReportDeleteSerializer(CustomSerializer):
    report_id = serializers.UUIDField()

    def validate_report_id(self, value):
        user = self.context["request"].user
        try:
            report = Report.objects.get(id=value)
        except Report.DoesNotExist:
            raise serializers.ValidationError("Hisobot topilmadi.")

        if report.organization != user.organization:
            raise serializers.ValidationError("Siz bu hisobotni o‘chira olmaysiz.")

        if report.status != Report.StatusChoices.SAVED:
            raise serializers.ValidationError("Faqat qoralama (saqlangan) hisobotni o‘chirish mumkin.")

        if not report.is_plant_based:
            raise serializers.ValidationError("Faqat ko‘chatga oid hisobotlar o‘chiriladi.")

        self.instance = report
        return value

    def delete(self):
        report = self.instance
        report.delete()
        return {"detail": "Hisobot o‘chirildi."}
