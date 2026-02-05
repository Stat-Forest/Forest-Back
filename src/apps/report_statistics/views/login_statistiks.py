from decimal import Decimal
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import (
    Report,
    ReportItem,
    Statement,
    StatementColumn,
    Deadline,
)
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
                description="Oylik: YYYY-MM"
            ),
            OpenApiParameter(
                name="yearly",
                type=OpenApiTypes.STR,
                required=False,
                description="Yillik: YYYY"
            ),
        ]
    )
    def get(self, request):
        monthly = request.query_params.get("monthly")
        yearly = request.query_params.get("yearly")

        print("=== QUERY PARAMS ===")
        print("monthly:", monthly)
        print("yearly:", yearly)
        print("====================")

        result = []

        for cfg in SUMMARY_CONFIG:
            print("\n==============================")
            print("CFG COLUMN:", cfg["column_name"])
            print("CFG PERIOD:", cfg["period"])
            print("==============================")

            # 1️⃣ STATEMENT
            statement = Statement.objects.filter(
                name_uz=cfg["statement_name"]
            ).first()

            print("STATEMENT NAME FROM CFG:", cfg["statement_name"])
            print("STATEMENT FOUND:", bool(statement))

            if not statement:
                print("❌ STATEMENT NOT FOUND, SKIP")
                continue

            print("✅ STATEMENT:", statement.id, statement.name_uz)

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            print("ALL DEADLINES:", list(
                deadline_qs.values_list("submit_at", flat=True)
            ))

            if cfg["period"] == "monthly" and monthly:
                deadline_qs = deadline_qs.filter(submit_at=monthly)
                print("📅 MONTHLY FILTER:", monthly)

            elif cfg["period"] == "yearly" and yearly:
                deadline_qs = deadline_qs.filter(submit_at=yearly)
                print("📅 YEARLY FILTER:", yearly)

            else:
                deadline_qs = deadline_qs.order_by("-created_at")
                print("📅 FALLBACK: LAST CREATED")

            deadline = deadline_qs.first()

            print("DEADLINE FOUND:", bool(deadline))
            if deadline:
                print("✅ DEADLINE:", deadline.id, deadline.submit_at)
            else:
                print("❌ DEADLINE NOT FOUND, SKIP")
                continue

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                is_report=True,
                status=Report.StatusChoices.ACCEPTED
            )

            print("REPORT COUNT:", reports.count())
            print(
                "REPORT STATUSES:",
                list(reports.values_list("status", flat=True))
            )

            if not reports.exists():
                print("❌ NO REPORTS FOUND")

            plan_value = Decimal("0")
            actual_value = Decimal("0")

            # 4️⃣ PLAN
            plan_cfg = cfg.get("plan")
            if plan_cfg:
                print("PLAN CFG:", plan_cfg)

                plan_column_qs = StatementColumn.objects.filter(
                    statement=statement,
                    title=plan_cfg["column_title"]
                )

                print(
                    "PLAN COLUMN BY TITLE:",
                    list(plan_column_qs.values_list("id", "title", "ordering"))
                )

                if plan_cfg.get("ordering"):
                    plan_column_qs = plan_column_qs.filter(
                        ordering=plan_cfg["ordering"]
                    )
                    print("PLAN ORDERING FILTER:", plan_cfg["ordering"])

                plan_column = plan_column_qs.first()
                print("PLAN COLUMN FOUND:", bool(plan_column))

                if plan_column:
                    plan_items_qs = ReportItem.objects.filter(
                        report__in=reports,
                        statement_column=plan_column
                    )

                    print("PLAN ITEMS COUNT:", plan_items_qs.count())

                    plan_value = (
                        plan_items_qs.aggregate(total=Sum("value"))["total"]
                        or Decimal("0")
                    )

                    print("✅ PLAN VALUE:", plan_value)

            # 5️⃣ ACTUAL
            actual_cfg = cfg["actual"]
            print("ACTUAL CFG:", actual_cfg)

            actual_column_qs = StatementColumn.objects.filter(
                statement=statement,
                title=actual_cfg["column_title"]
            )

            print(
                "ACTUAL COLUMN BY TITLE:",
                list(actual_column_qs.values_list("id", "title", "ordering"))
            )

            if actual_cfg.get("ordering"):
                actual_column_qs = actual_column_qs.filter(
                    ordering=actual_cfg["ordering"]
                )
                print("ACTUAL ORDERING FILTER:", actual_cfg["ordering"])

            actual_column = actual_column_qs.first()
            print("ACTUAL COLUMN FOUND:", bool(actual_column))

            if actual_column:
                actual_items_qs = ReportItem.objects.filter(
                    report__in=reports,
                    statement_column=actual_column
                )

                print("ACTUAL ITEMS COUNT:", actual_items_qs.count())

                actual_value = (
                    actual_items_qs.aggregate(total=Sum("value"))["total"]
                    or Decimal("0")
                )

                print("✅ ACTUAL VALUE:", actual_value)

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
