from apps.reports.models import Deadline
from apps.base.views import CustomListAPIView
from apps.reports.serializers import DeadlineSerializer

class DeadlineListView(CustomListAPIView):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    filterset_fields = ('statement','period')