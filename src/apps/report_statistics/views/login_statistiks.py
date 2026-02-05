from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import Report, ReportItem, Statement, StatementColumn, Deadline
from apps.report_statistics.serializers import ReportSummarySerializer
from apps.report_statistics.summary_config import SUMMARY_CONFIG


class ReportLoginSummaryAPIView(APIView):
    @extend_schema(
        tags=["Login Stats"],
        parameters=[
            OpenApiParameter(
                name="monthly",
                type=OpenApiTypes.STR,
                required=False,
                description="Oylik davr: YYYY-MM"
            ),
            OpenApiParameter(
                name="yearly",
                type=OpenApiTypes.STR,
                required=False,
                description="Yillik davr: YYYY"
            ),
        ]
    )
    def get(self, request):
        monthly = request.query_params.get("monthly")
        yearly = request.query_params.get("yearly")

        print("\n=== QUERY PARAMS ===")
        print("monthly:", monthly)
        print("yearly:", yearly)
        print("====================")

        result = []

        for cfg in SUMMARY_CONFIG:
            print("\n==============================")
            print("COLUMN NAME:", cfg["column_name"])
            print("STATEMENT NAME:", cfg["statement_name"])
            print("PERIOD:", cfg["period"])
            print("==============================")

            # 1️⃣ STATEMENT
            statement = Statement.objects.filter(name_uz=cfg["statement_name"]).first()
            if not statement:
                print("❌ STATEMENT NOT FOUND → SKIP")
                continue
            print("✅ STATEMENT ID:", statement.id)

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            if cfg["period"] == "monthly" and monthly:
                # Oylik filter
                deadline_qs = deadline_qs.filter(submit_at=monthly)
                print("APPLY MONTHLY FILTER:", monthly)
            elif cfg["period"] == "yearly" and yearly:
                # Yillik filter
                deadline_qs = deadline_qs.filter(submit_at=yearly)
                print("APPLY YEARLY FILTER:", yearly)
            else:
                # fallback → oxirgi yaratilgan deadline
                deadline_qs = deadline_qs.order_by("-created_at")
                print("FALLBACK → LAST CREATED DEADLINE")

            deadline = deadline_qs.first()
            if not deadline:
                print("❌ DEADLINE NOT FOUND → SKIP")
                continue
            print("✅ DEADLINE:", deadline.id, "| submit_at:", deadline.submit_at)

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                is_report=True,
            )
            if cfg["period"] in ["monthly", "yearly"]:
                # Agar oylik/yillik filter ishlatilsa, faqat ACCEPTED status
                reports = reports.filter(status=Report.StatusChoices.ACCEPTED)

            print("REPORT COUNT:", reports.count())
            if reports.count() == 0:
                print(f"⚠️ WARNING: No reports found for statement {statement.name_uz} and deadline {deadline.submit_at}")

            # 4️⃣ PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")
            if plan_cfg:
                plan_column = StatementColumn.objects.filter(id=plan_cfg["column_id"]).first()
                if plan_column:
                    plan_items_qs = ReportItem.objects.filter(
                        report__in=reports,
                        statement_column=plan_column
                    )
                    plan_value = sum(
                        Decimal(item.value) if item.value and item.value.strip() else Decimal("0")
                        for item in plan_items_qs
                    )

            # 5️⃣ ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")
            if actual_cfg:
                actual_column = StatementColumn.objects.filter(id=actual_cfg["column_id"]).first()
                if actual_column:
                    actual_items_qs = ReportItem.objects.filter(
                        report__in=reports,
                        statement_column=actual_column
                    )
                    actual_value = sum(
                        Decimal(item.value) if item.value and item.value.strip() else Decimal("0")
                        for item in actual_items_qs
                    )

            # 6️⃣ RESPONSE
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

        print("\n===== FINAL RESULT =====")
        print(result)
        print("========================")

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)
