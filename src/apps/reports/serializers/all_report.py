from apps.base.serializers import CustomModelSerializer
from apps.reports.models import AllReport


class AllReportListSerializer(CustomModelSerializer):
    class Meta:
        model = AllReport
        fields = ('id','title','count')