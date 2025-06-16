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

        base_qs = Deadline.objects.select_related(
            "statement", "statement__parent"
        ).prefetch_related(
            "organizations"
        )

        if not getattr(user, 'organization', None) or not getattr(user, 'statement', None):
            return base_qs.none()

        return base_qs.filter(
            organizations=user.organization,
            statement__parent=user.statement
        ).distinct()




