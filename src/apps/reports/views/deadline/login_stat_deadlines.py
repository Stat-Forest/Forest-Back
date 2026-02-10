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
        print("🔍 COMPREHENSIVE DEADLINE DEBUG")
        print("=" * 80)

        # ============ 1. CHECK ALL STATEMENTS ============
        print("\n📋 ALL STATEMENTS IN DATABASE:")
        all_statements = Statement.objects.filter(parent__isnull=False)
        for stmt in all_statements:
            print(f"  - ID: {stmt.id} | Name: '{stmt.name}' | Period: {stmt.period}")

        print(f"\n📊 Total child statements: {all_statements.count()}")

        # ============ 2. CHECK IF MONTHLY/YEARLY STATEMENTS EXIST ============
        print("\n🔎 Checking MONTHLY_STATEMENTS existence:")
        for stmt_name in MONTHLY_STATEMENTS:
            exists = Statement.objects.filter(name=stmt_name, parent__isnull=False).exists()
            print(f"  - '{stmt_name}': {'✅ EXISTS' if exists else '❌ NOT FOUND'}")

        print("\n🔎 Checking YEARLY_STATEMENTS existence:")
        for stmt_name in YEARLY_STATEMENTS:
            exists = Statement.objects.filter(name=stmt_name, parent__isnull=False).exists()
            print(f"  - '{stmt_name}': {'✅ EXISTS' if exists else '❌ NOT FOUND'}")

        # ============ 3. CHECK ALL DEADLINES ============
        print("\n📅 ALL DEADLINES IN DATABASE:")
        all_deadlines = Deadline.objects.select_related('statement').all()
        print(f"Total deadlines: {all_deadlines.count()}")
        for dl in all_deadlines[:20]:  # First 20 only
            print(f"  - ID: {dl.id} | Statement: '{dl.statement.name}' | Submit: {dl.submit_at}")

        # ============ 4. CHECK REPORTS ============
        print("\n📊 ACCEPTED REPORTS:")
        accepted_reports = Report.objects.filter(
            status=Report.StatusChoices.ACCEPTED,
            is_report=True
        ).select_related('deadline', 'deadline__statement', 'organization')

        print(f"Total ACCEPTED reports: {accepted_reports.count()}")
        for report in accepted_reports[:10]:  # First 10
            print(f"  - Report ID: {report.id}")
            print(f"    Deadline ID: {report.deadline_id}")
            print(f"    Statement: '{report.deadline.statement.name}'")
            print(f"    Organization: {report.organization.name if report.organization else 'None'}")
            print()

        # ============ 5. NOW RUN THE ACTUAL QUERY ============
        print("\n" + "=" * 80)
        print("🎯 RUNNING ACTUAL QUERYSET")
        print("=" * 80)

        qs = (
            Deadline.objects
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .distinct()
        )

        print(f"📊 Initial queryset count: {qs.count()}")

        # Period type filter
        period_type = self.request.query_params.get("period_type")
        print(f"\n🎯 Period type parameter: '{period_type}'")

        if period_type == "monthly":
            print(f"📌 Filtering by MONTHLY_STATEMENTS: {MONTHLY_STATEMENTS}")
            qs = qs.filter(statement__name__in=MONTHLY_STATEMENTS)
            print(f"✅ After monthly filter count: {qs.count()}")

        elif period_type == "yearly":
            print(f"📌 Filtering by YEARLY_STATEMENTS: {YEARLY_STATEMENTS}")
            qs = qs.filter(statement__name__in=YEARLY_STATEMENTS)
            print(f"✅ After yearly filter count: {qs.count()}")

        # Report existence filter
        print("\n🔎 Checking for accepted reports...")

        report_exists_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )

        qs = qs.annotate(has_report=Exists(report_exists_qs))

        print(f"\n📊 Deadlines with has_report annotation:")
        for deadline in qs:
            report_count = Report.objects.filter(
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
                is_report=True
            ).count()
            print(
                f"  - Deadline ID {deadline.id} ({deadline.statement.name}): has_report={deadline.has_report}, actual_reports={report_count}")

        qs = qs.filter(has_report=True)
        print(f"\n✅ Final queryset count after filter: {qs.count()}")

        final_qs = qs.order_by("-created_at")
        print("=" * 80 + "\n")

        return final_qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        context["user"] = self.request.user
        return context