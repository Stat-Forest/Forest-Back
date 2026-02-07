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
            print("REPORTS IDs:", list(reports.values_list('id', flat=True)))

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

                print(f"\n    🔍 Searching for column_id: {column_id}")

                # ReportItem'lardan qidirish
                items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                print(f"    📊 Found ReportItems: {items.count()}")

                for item in items:
                    print(f"    📄 Processing ReportItem ID: {item.id}")
                    print(f"       Direct value: {item.value}")

                    # Avval ReportItemInner mavjudligini tekshirish
                    inner_values = ReportItemInner.objects.filter(
                        report_item=item
                    )

                    print(f"       Found {inner_values.count()} inner values")

                    if inner_values.exists():
                        # Agar inner values bo'lsa, ularni yig'ish
                        for inner in inner_values:
                            try:
                                if inner.value and inner.value.strip() and inner.value.strip() not in ['', 'None',
                                                                                                       'null']:
                                    val = Decimal(inner.value.strip())
                                    total += val
                                    print(f"       ✅ Added inner value: {val} (total now: {total})")
                            except (InvalidOperation, ValueError, TypeError) as e:
                                print(f"       ⚠️ Invalid inner value: '{inner.value}' - {e}")
                    else:
                        # Agar inner yo'q bo'lsa, direct value ishlatish
                        try:
                            if item.value and item.value.strip() and item.value.strip() not in ['', 'None', 'null']:
                                val = Decimal(item.value.strip())
                                total += val
                                print(f"       ✅ Added direct value: {val} (total now: {total})")
                        except (InvalidOperation, ValueError, TypeError) as e:
                            print(f"       ⚠️ Invalid direct value: '{item.value}' - {e}")

                print(f"    💰 TOTAL for column {column_id}: {total}")
                return total

            # 4️⃣ PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")

            if plan_cfg:
                plan_column_id = plan_cfg["column_id"]
                print(f"\n📋 PLAN COLUMN ID: {plan_column_id}")

                plan_column = StatementColumn.objects.filter(id=plan_column_id).first()
                if not plan_column:
                    print(f"⚠️ WARNING: Plan column not found")
                else:
                    print(f"✅ PLAN COLUMN: {plan_column.title}")
                    plan_value = get_total_value(plan_column_id, reports)
                    print(f"📊 TOTAL PLAN VALUE: {plan_value}")

            # 5️⃣ ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")

            if actual_cfg:
                actual_column_id = actual_cfg["column_id"]
                print(f"\n📋 ACTUAL COLUMN ID: {actual_column_id}")

                actual_column = StatementColumn.objects.filter(id=actual_column_id).first()
                if not actual_column:
                    print(f"⚠️ WARNING: Actual column not found")
                else:
                    print(f"✅ ACTUAL COLUMN: {actual_column.title}")
                    actual_value = get_total_value(actual_column_id, reports)
                    print(f"📊 TOTAL ACTUAL VALUE: {actual_value}")

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