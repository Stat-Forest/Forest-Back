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

        result = []

        for cfg in SUMMARY_CONFIG:
            # 1️⃣ STATEMENT
            statement = Statement.objects.filter(
                name=cfg["statement_name"]
            ).first()
            print('11111',statement.name)

            if not statement:
                continue

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(
                statement=statement
            )
            

            if cfg["period"] == "monthly" and monthly:
                deadline_qs = deadline_qs.filter(submit_at=monthly)
                print('aaaaa')

            elif cfg["period"] == "yearly" and yearly:
                deadline_qs = deadline_qs.filter(submit_at=yearly)
                print('bbb')

            else:
                deadline_qs = deadline_qs.order_by("-created_at")
                print('sss')

            deadline = deadline_qs.first()
            if not deadline:
                # 🔒 himoya: 500 bo‘lmasin
                continue

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                is_report=True,
                status=Report.StatusChoices.ACCEPTED
            )

            plan_value = Decimal("0")
            actual_value = Decimal("0")

            # 4️⃣ PLAN
            plan_cfg = cfg.get("plan")
            if plan_cfg:
                plan_column_qs = StatementColumn.objects.filter(
                    statement=statement,
                    title=plan_cfg["column_title"]
                )

                if plan_cfg.get("ordering"):
                    plan_column_qs = plan_column_qs.filter(
                        ordering=plan_cfg["ordering"]
                    )

                plan_column = plan_column_qs.first()

                if plan_column:
                    plan_value = (
                        ReportItem.objects.filter(
                            report__in=reports,
                            statement_column=plan_column
                        )
                        .aggregate(total=Sum("value"))["total"]
                        or Decimal("0")
                    )

            # 5️⃣ ACTUAL
            actual_cfg = cfg["actual"]

            actual_column_qs = StatementColumn.objects.filter(
                statement=statement,
                title=actual_cfg["column_title"]
            )

            if actual_cfg.get("ordering"):
                actual_column_qs = actual_column_qs.filter(
                    ordering=actual_cfg["ordering"]
                )

            actual_column = actual_column_qs.first()

            if actual_column:
                actual_value = (
                    ReportItem.objects.filter(
                        report__in=reports,
                        statement_column=actual_column
                    )
                    .aggregate(total=Sum("value"))["total"]
                    or Decimal("0")
                )

            # 6️⃣ RESPONSE
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)
