from django.db.models import Exists, OuterRef

from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline import DeadlineSerializer


from rest_framework import generics
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes


@extend_schema(
    tags=["Deadlines"],
    parameters=[
        OpenApiParameter(
            name="is_new_deadline",
            type=OpenApiTypes.BOOL,
            required=False,
            description=(
                "true → shu organization uchun hali report yaratilmagan deadlinelar\n"
                "false → shu organization uchun report yaratilgan deadlinelar"
            ),
        ),
    ],
)
@extend_schema(tags=["Deadlines"])
class DeadlineListAPIView(generics.ListAPIView):
    serializer_class = DeadlineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["statement", "statement__period", "deadline_at"]

    def get_queryset(self):
        user = self.request.user

        qs = Deadline.objects.select_related(
            "statement", "statement__parent"
        ).prefetch_related("organizations")

        user_org = getattr(user, "organization", None)

        if user_org:
            qs = qs.filter(organizations=user_org)
        elif getattr(user, "statement", None):
            qs = qs.filter(statement__parent_id=user.statement.pk)
        else:
            return Deadline.objects.none()

        # === is_new_deadline filter ===
        is_new_deadline = self.request.query_params.get("is_new_deadline")

        if is_new_deadline is not None and user_org:
            report_exists_qs = Report.objects.filter(
                deadline=OuterRef("pk"),
                organization=user_org
            )

            if is_new_deadline.lower() == "true":
                qs = qs.annotate(
                    has_report=Exists(report_exists_qs)
                ).filter(has_report=False)

            elif is_new_deadline.lower() == "false":
                qs = qs.annotate(
                    has_report=Exists(report_exists_qs)
                ).filter(has_report=True)

        return qs.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        return context

