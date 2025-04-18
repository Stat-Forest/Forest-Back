from apps.base.views import CustomListAPIView
from apps.reports.models import AllReview
from apps.reports.serializers import AllReviewListSerializer


class AllReviewtListAPIView(CustomListAPIView):
    queryset = AllReview.objects.all()
    serializer_class = AllReviewListSerializer