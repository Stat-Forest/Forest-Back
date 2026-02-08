from decimal import Decimal, InvalidOperation
from django.db.models import Q, Sum, F, DecimalField
from django.db.models.functions import Cast

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

        print("\n" + "=" * 60)
        print("QUERY PARAMS:")
        print(f"  monthly: {monthly}")
        print(f"  yearly: {yearly}")
        print("=" * 60)

        result = []

        for cfg in SUMMARY_CONFIG:
            print(f"\n{'=' * 60}")
            print(f"Processing: {cfg['column_name']}")
            print(f"Statement: {cfg['statement_name']}")
            print(f"Period: {cfg['period']}")
            print(f"{'=' * 60}")

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

            print(f"✅ Statement found: ID={statement.id}, name={statement.name}")

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            # Period detection based on submit_at format:
            # - Yearly: "2025" (4 chars)
            # - Monthly: "2025-01" (7 chars, contains '-', no 'CHORAK')
            # - Quarterly: "2025-CHORAK_1" (contains 'CHORAK')

            if cfg["period"] == "monthly":
                if monthly:
                    deadline_qs = deadline_qs.filter(submit_at=monthly)
                    print(f"📅 Filtered by monthly: {monthly}")
                else:
                    # Latest monthly deadline
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(
                        submit_len=7,
                        submit_at__contains='-'
                    ).exclude(
                        submit_at__contains='CHORAK'
                    ).order_by("-created_at")
                    print("📅 Using latest monthly deadline")

            elif cfg["period"] == "yearly":
                if yearly:
                    deadline_qs = deadline_qs.filter(submit_at=yearly)
                    print(f"📅 Filtered by yearly: {yearly}")
                else:
                    # Latest yearly deadline
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(submit_len=4).order_by("-created_at")
                    print("📅 Using latest yearly deadline")
            else:
                deadline_qs = deadline_qs.order_by("-created_at")
                print("📅 Using latest deadline (any period)")

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

            print(f"✅ Deadline found: ID={deadline.id}, submit_at={deadline.submit_at}")

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
            )

            report_count = reports.count()
            print(f"📊 Found {report_count} accepted reports")

            if report_count == 0:
                print("⚠️  No accepted reports found")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            print(f"   Report IDs: {list(reports.values_list('id', flat=True)[:5])}{'...' if report_count > 5 else ''}")

            # 4️⃣ OPTIMIZED VALUE EXTRACTION
            def get_total_value(column_id, reports_qs):
                """
                Optimized function to sum values from ReportItemInner for a given column
                across multiple reports.
                """
                print(f"\n  🔍 Extracting values for column_id: {column_id}")

                # Get ReportItems for this column
                report_items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                item_count = report_items.count()
                print(f"  📝 Found {item_count} ReportItems")

                if item_count == 0:
                    print(f"  ⚠️  No ReportItems found for column {column_id}")
                    return Decimal("0")

                # Get all inner values
                inners = ReportItemInner.objects.filter(
                    report_item__in=report_items
                )

                inner_count = inners.count()
                print(f"  📦 Found {inner_count} ReportItemInners")

                total = Decimal("0")

                if inner_count > 0:
                    # Sum from inners
                    for inner in inners:
                        if inner.value:
                            value_str = str(inner.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                except (InvalidOperation, ValueError, TypeError) as e:
                                    print(f"  ⚠️  Invalid inner value: '{inner.value}' - {e}")
                else:
                    # Fallback to direct values from ReportItem
                    print("  ℹ️  No inners found, using direct ReportItem values")
                    for item in report_items:
                        if item.value:
                            value_str = str(item.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                except (InvalidOperation, ValueError, TypeError) as e:
                                    print(f"  ⚠️  Invalid item value: '{item.value}' - {e}")

                print(f"  💰 TOTAL: {total}")
                return total

            # 5️⃣ CALCULATE PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")

            if plan_cfg:
                plan_column_id = plan_cfg["column_id"]
                print(f"\n📋 Processing PLAN (column_id: {plan_column_id})")

                plan_column = StatementColumn.objects.filter(id=plan_column_id).first()
                if plan_column:
                    print(f"   Column: {plan_column.title}")
                    plan_value = get_total_value(plan_column_id, reports)
                else:
                    print(f"   ⚠️  Plan column not found")

            # 6️⃣ CALCULATE ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")

            if actual_cfg:
                actual_column_id = actual_cfg["column_id"]
                print(f"\n📋 Processing ACTUAL (column_id: {actual_column_id})")

                actual_column = StatementColumn.objects.filter(id=actual_column_id).first()
                if actual_column:
                    print(f"   Column: {actual_column.title}")
                    actual_value = get_total_value(actual_column_id, reports)
                else:
                    print(f"   ⚠️  Actual column not found")

            # 7️⃣ ADD TO RESULT
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

            print(f"\n✅ Result: plan={plan_value}, actual={actual_value}")

        print("\n" + "=" * 60)
        print("FINAL RESULTS:")
        print("=" * 60)
        for item in result:
            print(f"{item['column_name']:60s} | Plan: {item['plan']:>10} | Actual: {item['actual']:>10}")
        print("=" * 60 + "\n")

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)