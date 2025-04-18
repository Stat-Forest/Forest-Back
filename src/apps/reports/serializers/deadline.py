from apps.base.serializers import CustomModelSerializer
from apps.reports.models.deadline import Deadline


class DeadlineListSerializer(CustomModelSerializer):
    class Meta:
        model = Deadline
        fields = '__all__'