from datetime import date
from rest_framework import generics
from drf_spectacular.utils import extend_schema

from apps.reports.models import Deadline
from apps.reports.serializers.deadline.expired_deadlines import DeadlineExpiredSerializer


@extend_schema(tags=["Deadlines"])
class DeadlineExpiredListAPIView(generics.ListAPIView):
    serializer_class = DeadlineExpiredSerializer

    def get_queryset(self):
        today = date.today()
        return Deadline.objects.filter(
            deadline_at__lt=today
        ).select_related(
            "statement", "statement__parent"
        ).prefetch_related(
            "organizations"
        ).order_by("deadline_at")
