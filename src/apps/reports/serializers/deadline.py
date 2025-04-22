from apps.reports.models import Deadline
from apps.base.serializers import CustomModelSerializer

class DeadlineSerializer(CustomModelSerializer):
    class Meta:
        model = Deadline
        fields = '__all__'