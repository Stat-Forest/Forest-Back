from apps.reports.models import ReportItem

from rest_framework import serializers

class ReportItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = ReportItem
        fields = ['id', 'statement_column', 'value']

