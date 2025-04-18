from apps.base.serializers import CustomModelSerializer
from apps.reports.models import Review


class ReviewListSerializer(CustomModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'