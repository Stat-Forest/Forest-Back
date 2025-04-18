from apps.base.serializers import CustomModelSerializer
from apps.reports.models import AllReview


class AllReviewListSerializer(CustomModelSerializer):
    class Meta:
        model = AllReview
        fields = ('id','title','count')