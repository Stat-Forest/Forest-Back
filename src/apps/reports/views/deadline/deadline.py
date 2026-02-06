from django.db.models import Exists, OuterRef

from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline import DeadlineSerializer
from apps.users.models import CustomUser

from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    tags=["Deadlines"],
    parameters=[
        OpenApiParameter(
            name="is_new_deadline",
            type=OpenApiTypes.BOOL,
            required=False,
            description=(
                "true → hali regiondagi organizationlardan report yo‘q\n"
                "false → kamida bitta organization report yuborgan"
            ),
        ),
    ],
)
class DeadlineListAPIView(generics.ListAPIView):
    serializer_class = DeadlineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["statement", "statement__period", "deadline_at"]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Deadline.objects
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .distinct()
        )

        # ================= HUDUDIY_BOSHQARMA =================
        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = user.region_user_orgs.all()

            qs = qs.filter(
                organizations__in=orgs
            )

        # ================= ORGANIZATION =================
        elif user.organization:
            qs = qs.filter(
                organizations=user.organization
            )

        # ================= STATEMENT =================
        elif user.statement:
            qs = qs.filter(
                statement__parent_id=user.statement.pk
            )

        # ================= SUPER =================
        else:
            pass

        # ================= is_new_deadline =================
        is_new_deadline = self.request.query_params.get("is_new_deadline")

        if is_new_deadline is not None:

            report_exists_qs = Report.objects.filter(
                deadline=OuterRef("pk"),
                status=Report.StatusChoices.ACCEPTED,
                is_report=True,
            )

            # 🔥 HUDUDIY_BOSHQARMA → faqat region_user_orgs
            if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
                report_exists_qs = report_exists_qs.filter(
                    organization__in=user.region_user_orgs.all()
                )

            # ORGANIZATION
            elif user.organization:
                report_exists_qs = report_exists_qs.filter(
                    organization=user.organization
                )

            qs = qs.annotate(
                has_report=Exists(report_exists_qs)
            )

            if is_new_deadline.lower() == "true":
                qs = qs.filter(has_report=False)
            elif is_new_deadline.lower() == "false":
                qs = qs.filter(has_report=True)

        return qs.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        return context
