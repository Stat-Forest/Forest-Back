from django.db.models import Exists, OuterRef, Q
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.reports.models import Deadline, Report, Statement
from apps.reports.serializers.deadline import DeadlineReportListSerializer

# Statement name constants
MONTHLY_STATEMENTS = [
    "Dorivor yetishtirish",
    "O'rmon barpo qilish bo'limi",
    "Ko'chatxona va Niholxona Jami",
    "Tut Ko'chat va Tut Nihol"
]

YEARLY_STATEMENTS = [
    "O'rmon bilan qoplangan yerlar",
    "Yer o'zlashtirish"
]


@extend_schema(
    tags=["Deadlines"],
    parameters=[
        OpenApiParameter(
            name="period_type",
            type=OpenApiTypes.STR,
            required=False,
            description=(
                    "monthly → Oylik hisobotlar uchun\n"
                    "yearly → Yillik hisobotlar uchun"
            ),
            enum=["monthly", "yearly"]
        )
    ],
)
class DeadlineLoginStatListAPIView(generics.ListAPIView):
    serializer_class = DeadlineReportListSerializer

    def get_queryset(self):
        qs = (
            Deadline.objects
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .distinct()
        )

        # ================= PERIOD TYPE FILTER (monthly/yearly) =================
        period_type = self.request.query_params.get("period_type")

        if period_type == "monthly":
            # Filter by name_uz field
            qs = qs.filter(statement__name_uz__in=MONTHLY_STATEMENTS)

        elif period_type == "yearly":
            # Filter by name_uz field
            qs = qs.filter(statement__name_uz__in=YEARLY_STATEMENTS)

        # ================= FILTER: Only deadlines with accepted reports =================
        report_exists_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )

        qs = qs.annotate(has_report=Exists(report_exists_qs)).filter(has_report=True)

        return qs.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        context["user"] = self.request.user
        return context