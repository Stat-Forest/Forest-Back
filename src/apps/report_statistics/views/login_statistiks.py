from decimal import Decimal, InvalidOperation
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import Report, ReportItem, ReportItemInner, Statement, StatementColumn, Deadline
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

        result = []

        for cfg in SUMMARY_CONFIG:
            # 1️⃣ STATEMENT - support both name and name_uz
            statement = Statement.objects.filter(
                Q(name=cfg["statement_name"]) |
                Q(name_uz=cfg["statement_name"]) |
                Q(name__iexact=cfg["statement_name"]) |
                Q(name_uz__iexact=cfg["statement_name"])
            ).first()

            if not statement:
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            if cfg["period"] == "monthly":
                if monthly:
                    deadline_qs = deadline_qs.filter(submit_at=monthly)
                else:
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(
                        submit_len=7,
                        submit_at__contains='-'
                    ).exclude(
                        submit_at__icontains='CHORAK'
                    ).order_by("-created_at")

            elif cfg["period"] == "yearly":
                if yearly:
                    deadline_qs = deadline_qs.filter(submit_at=yearly)
                else:
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(submit_len=4).order_by("-created_at")
            else:
                deadline_qs = deadline_qs.order_by("-created_at")

            deadline = deadline_qs.first()

            if not deadline:
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
            )

            if reports.count() == 0:
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # 4️⃣ VALUE EXTRACTION
            def get_total_value(column_id, reports_qs):
                if not column_id:
                    return Decimal("0")

                # Check if column exists
                if not StatementColumn.objects.filter(id=column_id).exists():
                    return Decimal("0")

                # Get ReportItems
                report_items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                if report_items.count() == 0:
                    return Decimal("0")

                # Get ReportItemInners
                inners = ReportItemInner.objects.filter(
                    report_item__in=report_items
                )

                total = Decimal("0")

                if inners.count() > 0:
                    # Sum from inners
                    for inner in inners:
                        if inner.value:
                            value_str = str(inner.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    total += Decimal(value_str)
                                except (InvalidOperation, ValueError, TypeError):
                                    pass
                else:
                    # Fallback to ReportItem.value
                    for item in report_items:
                        if item.value:
                            value_str = str(item.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    total += Decimal(value_str)
                                except (InvalidOperation, ValueError, TypeError):
                                    pass

                return total

            # 5️⃣ CALCULATE PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get('plan')
            if plan_cfg:
                plan_column_id = plan_cfg.get('column_id')
                if plan_column_id:
                    plan_value = get_total_value(plan_column_id, reports)

            # 6️⃣ CALCULATE ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get('actual')
            if actual_cfg:
                actual_column_id = actual_cfg.get('column_id')
                if actual_column_id:
                    actual_value = get_total_value(actual_column_id, reports)

            # 7️⃣ ADD TO RESULT
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)