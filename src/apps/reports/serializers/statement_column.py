from apps.reports.models import StatementColumn
from apps.base.serializers import CustomModelSerializer


class StatementColumnListSerializer(CustomModelSerializer):
    class Meta:
        model = StatementColumn
        fields = ['id', 'title', 'ordering', 'statement']
