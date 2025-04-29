# serializers.py
from rest_framework import serializers
from apps.reports.models import Report

class ReportSendSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'status']

    def update(self, instance, validated_data):
        instance.status = Report.StatusChoices.SENT
        instance.save()
        return instance
