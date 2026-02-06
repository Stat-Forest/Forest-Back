from rest_framework import serializers


class ReportSummarySerializer(serializers.Serializer):
    column_name = serializers.CharField()
    unit = serializers.CharField()
    plan = serializers.DecimalField(max_digits=30, decimal_places=2)
    actual = serializers.DecimalField(max_digits=30, decimal_places=2)
