from rest_framework import serializers

from apps.base.serializers import CustomSerializer
from apps.reports.models import Report


class ReportAggregateSelectSerializer(CustomSerializer):
    report_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )


    def validate_report_ids(self, value):
        reports = Report.objects.filter(id__in=value, status=Report.StatusChoices.ACCEPTED)
        if not reports.exists():
            raise serializers.ValidationError("Hech qanday qabul qilingan report topilmadi.")
        if reports.count() != len(value):
            raise serializers.ValidationError("Ba'zi reportlar mavjud emas yoki hali qabul qilinmagan.")
        return value


{
  "report_ids": ["37c9546e-f273-466e-a455-7a30e9ecba63", "142ba6dd-4ea8-47a3-9155-a9be33632a57"]
}