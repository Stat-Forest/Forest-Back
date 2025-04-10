from src.apps.base.serializers import CustomModelSerializer
from src.apps.reports.models import Report


class ReportListSerializer(CustomModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'