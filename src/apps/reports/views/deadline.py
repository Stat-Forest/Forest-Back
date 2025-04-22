from rest_framework import generics
from apps.reports.models import Deadline
from apps.reports.serializers import DeadlineSerializer

class DeadlineListView(generics.ListAPIView):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    filterset_fields = ('statement','period')