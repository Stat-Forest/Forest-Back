from rest_framework import serializers

from apps.reports.models import Report, ReportItem
from apps.base.serializers import CustomModelSerializer
from apps.reports.serializers.report_item import ReportItemSerializer


class ReportCreateSerializer(CustomModelSerializer):
    report_items = ReportItemSerializer(many=True)

    class Meta:
        model = Report
        fields = ['id', 'organization', 'statement', 'report_items']

    def create(self, validated_data):
        items_data = validated_data.pop('report_items')
        report = Report.objects.create(status=Report.StatusChoices.NEW, **validated_data)
        for item_data in items_data:
            ReportItem.objects.create(report=report, **item_data)
        return report


class ReportListSerializer(CustomModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'organization', 'statement', 'status']


class ReportDetailSerializer(CustomModelSerializer):
    report_items = ReportItemSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'organization', 'statement', 'status', 'report_items']


class ReportStatusUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Report
        fields = ['status']

    def validate_status(self, value):
        valid_statuses = [choice[0] for choice in Report.StatusChoices.choices]
        if value not in valid_statuses:
            raise serializers.ValidationError("Noto‘g‘ri status tanlandi.")
        return value