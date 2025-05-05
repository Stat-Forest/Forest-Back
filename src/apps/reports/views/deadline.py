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
        personal_info = getattr(user, "personal_info", None)

        base_qs = Deadline.objects.select_related(
            "statement", "statement__parent"
        ).prefetch_related(
            "organizations"
        )

        if not personal_info or not personal_info.organizations.exists():
            return base_qs

        user_organizations = personal_info.organizations.all()
        return base_qs.filter(organizations__in=user_organizations).distinct()


