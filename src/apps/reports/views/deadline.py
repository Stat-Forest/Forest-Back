from rest_framework import generics
from apps.reports.models import Deadline
from apps.reports.serializers import DeadlineSerializer

class DeadlineListAPIView(generics.ListAPIView):
    serializer_class = DeadlineSerializer

    def get_queryset(self):
        return Deadline.objects.prefetch_related(
            'organizations',
        ).select_related(
            'statement'
        ).filter(
            statement__parent__isnull=False
        )
