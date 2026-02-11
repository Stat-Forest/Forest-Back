from rest_framework import serializers
from decimal import Decimal


class ReportSummarySerializer(serializers.Serializer):
    column_name = serializers.CharField()
    unit = serializers.CharField()
    plan = serializers.DecimalField(max_digits=20, decimal_places=2)
    actual = serializers.DecimalField(max_digits=20, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()