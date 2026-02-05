from decimal import Decimal, InvalidOperation
from django.db.models import Q, Sum, F

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
            statement = Statement.objects.filter(
                Q(name=cfg["statement_name"]) | Q(name_uz=cfg["statement_name"])
            ).first()

            if not statement:
                print(f"❌ STATEMENT NOT FOUND: {cfg['statement_name']}")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue
            print("✅ STATEMENT ID:", statement.id, "| name:", statement.name)

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            if cfg["period"] == "monthly" and monthly:
                deadline_qs = deadline_qs.filter(submit_at=monthly)
                print("APPLY MONTHLY FILTER:", monthly)
            elif cfg["period"] == "yearly" and yearly:
                deadline_qs = deadline_qs.filter(submit_at=yearly)
                print("APPLY YEARLY FILTER:", yearly)
            else:
                deadline_qs = deadline_qs.order_by("-created_at")
                print("FALLBACK → LAST CREATED DEADLINE")

            deadline = deadline_qs.first()
            if not deadline:
                print("❌ DEADLINE NOT FOUND")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue
            print("✅ DEADLINE:", deadline.id, "| submit_at:", deadline.submit_at)

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
                is_report=True,
            )

            print("REPORT COUNT:", reports.count())

            # Report plant_based ekanligini tekshirish
            has_plant_based = reports.filter(is_plant_based=True).exists()
            print("HAS PLANT_BASED REPORTS:", has_plant_based)

            if reports.count() == 0:
                print(f"⚠️ WARNING: No accepted reports found")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # Helper function to get value from ReportItem or ReportItemInner
            def get_total_value(column_id, reports_qs):
                total = Decimal("0")

                # ReportItem'lardan qidirish
                items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                ).exclude(
                    Q(value__isnull=True) | Q(value='') | Q(value='None')
                )

                print(f"    Direct ReportItem count: {items.count()}")

                for item in items:
                    # Agar ReportItemInner mavjud bo'lsa, undan olish
                    inner_values = ReportItemInner.objects.filter(
                        report_item=item
                    ).exclude(
                        Q(value__isnull=True) | Q(value='') | Q(value='None')
                    )

                    if inner_values.exists():
                        print(f"    Using ReportItemInner (count: {inner_values.count()})")
                        for inner in inner_values:
                            try:
                                if inner.value and inner.value.strip():
                                    val = Decimal(inner.value.strip())
                                    total += val
                                    print(f"      + Inner value: {val}")
                            except (InvalidOperation, ValueError) as e:
                                print(f"      ⚠️ Invalid inner value: '{inner.value}' - {e}")
                    else:
                        # Aks holda ReportItem.value dan olish
                        try:
                            if item.value and item.value.strip():
                                val = Decimal(item.value.strip())
                                total += val
                                print(f"      + Direct value: {val}")
                        except (InvalidOperation, ValueError) as e:
                            print(f"      ⚠️ Invalid value: '{item.value}' - {e}")

                return total

            # 4️⃣ PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")

            if plan_cfg:
                plan_column_id = plan_cfg["column_id"]
                print(f"PLAN COLUMN ID: {plan_column_id}")

                plan_column = StatementColumn.objects.filter(id=plan_column_id).first()
                if not plan_column:
                    print(f"⚠️ WARNING: Plan column not found")
                else:
                    print(f"✅ PLAN COLUMN: {plan_column.title}")
                    plan_value = get_total_value(plan_column_id, reports)
                    print(f"TOTAL PLAN VALUE: {plan_value}")

            # 5️⃣ ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")

            if actual_cfg:
                actual_column_id = actual_cfg["column_id"]
                print(f"ACTUAL COLUMN ID: {actual_column_id}")

                actual_column = StatementColumn.objects.filter(id=actual_column_id).first()
                if not actual_column:
                    print(f"⚠️ WARNING: Actual column not found")
                else:
                    print(f"✅ ACTUAL COLUMN: {actual_column.title}")
                    actual_value = get_total_value(actual_column_id, reports)
                    print(f"TOTAL ACTUAL VALUE: {actual_value}")

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