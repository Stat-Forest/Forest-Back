from apps.base.serializers import CustomModelSerializer
from apps.reports.models import ReportItem


class ReportItemSerializer(CustomModelSerializer):
    class Meta:
        model = ReportItem
        fields = ['id', 'report', 'statement_column', 'value']
        read_only_fields = ['report']
