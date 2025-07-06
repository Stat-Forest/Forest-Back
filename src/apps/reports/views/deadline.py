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

        if user_org :
            qs = qs.filter(
                organizations=user_org,
            )
        elif user.statement is not None:
            qs = qs.filter(
                statement__parent_id=user.statement.pk,
            )

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context