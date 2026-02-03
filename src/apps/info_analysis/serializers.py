from rest_framework import serializers


class ReportDashboardItemSerializer(serializers.Serializer):
    parent_column_title = serializers.CharField()
    column_title = serializers.CharField()
    value = serializers.FloatField()
