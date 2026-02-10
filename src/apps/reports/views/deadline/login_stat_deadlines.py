from django.db.models import Exists, OuterRef
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
        print("\n" + "=" * 80)
        print("🔍 DEADLINE QUERYSET DEBUG")
        print("=" * 80)

        # Initial queryset
        qs = (
            Deadline.objects
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .distinct()
        )

        print(f"📊 Initial queryset count: {qs.count()}")
        print(f"📋 All deadlines: {list(qs.values_list('id', 'statement__name', 'submit_at'))}")

        # ================= PERIOD TYPE FILTER (monthly/yearly) =================
        period_type = self.request.query_params.get("period_type")
        print(f"\n🎯 Period type parameter: '{period_type}'")

        if period_type == "monthly":
            print(f"📌 Filtering by MONTHLY_STATEMENTS: {MONTHLY_STATEMENTS}")
            qs = qs.filter(statement__name__in=MONTHLY_STATEMENTS)
            print(f"✅ After monthly filter count: {qs.count()}")
            print(f"📋 Filtered deadlines: {list(qs.values_list('id', 'statement__name'))}")

        elif period_type == "yearly":
            print(f"📌 Filtering by YEARLY_STATEMENTS: {YEARLY_STATEMENTS}")
            qs = qs.filter(statement__name__in=YEARLY_STATEMENTS)
            print(f"✅ After yearly filter count: {qs.count()}")
            print(f"📋 Filtered deadlines: {list(qs.values_list('id', 'statement__name'))}")

        # ================= FILTER: Only deadlines with accepted reports =================
        print("\n🔎 Checking for accepted reports...")

        # Check all reports first
        all_reports = Report.objects.filter(
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )
        print(f"📊 Total ACCEPTED reports: {all_reports.count()}")
        print(f"📋 Report details: {list(all_reports.values_list('id', 'deadline_id', 'organization__name'))}")

        report_exists_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )

        qs_before_report_filter = qs.count()
        qs = qs.annotate(has_report=Exists(report_exists_qs))

        # Check annotation results
        print(f"\n📊 Deadlines with has_report annotation:")
        for deadline in qs:
            print(f"  - Deadline ID {deadline.id} ({deadline.statement.name}): has_report={deadline.has_report}")

        qs = qs.filter(has_report=True)
        print(f"\n✅ Before report filter: {qs_before_report_filter}")
        print(f"✅ After has_report=True filter: {qs.count()}")
        print(f"📋 Final deadlines: {list(qs.values_list('id', 'statement__name', 'submit_at'))}")

        final_qs = qs.order_by("-created_at")
        print(f"\n🎯 Final ordered queryset count: {final_qs.count()}")
        print(f"📋 Final ordered IDs: {list(final_qs.values_list('id', flat=True))}")
        print("=" * 80 + "\n")

        return final_qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        context["user"] = self.request.user

        print(f"\n👤 Serializer context - User: {self.request.user}")
        print(f"👤 User role: {self.request.user.role if hasattr(self.request.user, 'role') else 'N/A'}")
        print(f"🌐 Language: {context['lang']}\n")

        return context