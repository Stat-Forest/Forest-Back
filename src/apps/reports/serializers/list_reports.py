from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    report_items = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization','organization__name',
            'statement','statement__name',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items'
        )

    def get_report_items(self, obj):
        items = obj.report_items.all()
        result = []

        for item in items:
            if item.plant_id:
                ser = ReportItemPlantValueSerializer(item)
            else:
                ser = ReportItemSerializer(item, context=self.context)
            result.append(ser.data)

        return result