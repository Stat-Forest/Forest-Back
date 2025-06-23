from apps.reports.models import Deadline
from apps.reports.serializers import DeadlineSerializer

from rest_framework import generics
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Deadlines"])
class DeadlineListAPIView(generics.ListAPIView):
    serializer_class = DeadlineSerializer
    filterset_fields = ["statement", "statement__period"]

    def get_queryset(self):
        user = self.request.user

        qs = Deadline.objects.select_related(
            "statement", "statement__parent"
        ).prefetch_related(
            "organizations"
        )

        user_org = getattr(user, 'organization', None)
        user_stmt = getattr(user, 'statement', None)

        if user_org and user_stmt:
            qs = qs.filter(
                organizations=user_org,
                statement__parent=user_stmt
            )

        return qs
