from rest_framework import serializers
from apps.reports.models import ReportItem
from apps.general.models import Organization
import uuid

class ReportItemSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ReportItem
        fields = ['statement_column', 'value']

    def get_value(self, obj):
        try:
            org_id = uuid.UUID(str(obj.value))
            org = Organization.objects.filter(id=org_id).first()
            if org:
                return org.name
        except (ValueError, TypeError):
            pass

        return obj.value


