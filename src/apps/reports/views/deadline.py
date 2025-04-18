from apps.base.views import CustomListAPIView
from apps.reports.models.deadline import Deadline
from apps.reports.serializers.deadline import DeadlineListSerializer


class DeadlineListAPIView(CustomListAPIView):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineListSerializer