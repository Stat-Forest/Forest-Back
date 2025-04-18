
from apps.base.views import CustomListAPIView
from apps.reports.models import Review
from apps.reports.serializers import ReviewListSerializer


class ReportListAPIView(CustomListAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewListSerializer
