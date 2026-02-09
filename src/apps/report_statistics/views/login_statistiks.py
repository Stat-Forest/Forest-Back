from decimal import Decimal, InvalidOperation
from django.db.models import Q
from django.db.models.functions import Length

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

        print("\n" + "=" * 80)
        print(f"REQUEST PARAMS: monthly={monthly}, yearly={yearly}")
        print("=" * 80)

        result = []

        for cfg in SUMMARY_CONFIG:
            print(f"\n{'=' * 80}")
            print(f"CONFIG: {cfg['column_name']}")
            print(f"  statement_name: {cfg['statement_name']}")
            print(f"  period: {cfg['period']}")

            # 1️⃣ STATEMENT
            statement = Statement.objects.filter(
                Q(name=cfg["statement_name"]) |
                Q(name_uz=cfg["statement_name"]) |
                Q(name__iexact=cfg["statement_name"]) |
                Q(name_uz__iexact=cfg["statement_name"])
            ).first()

            if not statement:
                print(f"  ❌ STATEMENT NOT FOUND")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            print(
                f"  ✅ STATEMENT FOUND: id={statement.id}, name={statement.name}, name_uz={getattr(statement, 'name_uz', 'N/A')}")

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            config_period = cfg["period"]
            print(f"  🔍 Searching deadline for period: {config_period}")

            if config_period == "monthly":
                if monthly:
                    print(f"     Using monthly parameter: {monthly}")
                    deadline_qs = deadline_qs.filter(submit_at=monthly)
                else:
                    print(f"     Using latest monthly deadline")
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(
                        submit_len=7,
                        submit_at__contains='-'
                    ).exclude(
                        submit_at__icontains='CHORAK'
                    ).order_by("-submit_at", "-created_at")

            elif config_period == "yearly":
                if yearly:
                    print(f"     Using yearly parameter: {yearly}")
                    deadline_qs = deadline_qs.filter(submit_at=yearly)
                else:
                    print(f"     Using latest yearly deadline")
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(submit_len=4).order_by("-submit_at", "-created_at")
            else:
                print(f"     Using latest deadline (any period)")
                deadline_qs = deadline_qs.order_by("-created_at")

            # Show available deadlines
            all_deadlines = list(Deadline.objects.filter(statement=statement).values('id', 'submit_at')[:10])
            print(f"     Available deadlines: {[d['submit_at'] for d in all_deadlines]}")

            deadline = deadline_qs.first()

            if not deadline:
                print(f"  ❌ DEADLINE NOT FOUND")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            print(f"  ✅ DEADLINE FOUND: id={deadline.id}, submit_at={deadline.submit_at}")

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
            )

            report_count = reports.count()
            print(f"  📊 REPORTS: {report_count} accepted reports found")

            if report_count > 0:
                print(f"     Report IDs: {list(reports.values_list('id', flat=True)[:5])}")
            else:
                # Debug: check other statuses
                all_status_reports = Report.objects.filter(
                    statement=statement,
                    deadline=deadline
                ).values('id', 'status')[:5]
                print(f"     All status reports: {list(all_status_reports)}")

            if report_count == 0:
                print(f"  ⚠️  No accepted reports, returning 0")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # 4️⃣ VALUE EXTRACTION
            def get_total_value(column_id, reports_qs, label):
                print(f"  🔢 {label}: column_id={column_id}")

                if not column_id:
                    print(f"     ⚠️  No column_id provided")
                    return Decimal("0")

                # Check if column exists
                col_exists = StatementColumn.objects.filter(id=column_id).exists()
                if not col_exists:
                    print(f"     ❌ Column does not exist")
                    return Decimal("0")

                col_info = StatementColumn.objects.filter(id=column_id).values('statement_id', 'title_uz').first()
                print(
                    f"     Column: {col_info.get('title_uz', 'N/A')} (statement: {col_info.get('statement_id', 'N/A')})")

                # Get ReportItems
                report_items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                item_count = report_items.count()
                print(f"     ReportItems: {item_count}")

                if item_count == 0:
                    # Debug: show available columns
                    available_cols = list(ReportItem.objects.filter(
                        report__in=reports_qs
                    ).values_list('statement_column_id', flat=True).distinct()[:10])
                    print(f"     Available columns in reports: {available_cols}")
                    return Decimal("0")

                # Get ReportItemInners
                inners = ReportItemInner.objects.filter(
                    report_item__in=report_items
                )

                inner_count = inners.count()
                print(f"     ReportItemInners: {inner_count}")

                total = Decimal("0")
                processed = 0

                if inner_count > 0:
                    for inner in inners:
                        if inner.value:
                            value_str = str(inner.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                    processed += 1
                                    if processed <= 3:
                                        print(f"        + {val}")
                                except (InvalidOperation, ValueError, TypeError):
                                    pass
                else:
                    for item in report_items:
                        if item.value:
                            value_str = str(item.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                    processed += 1
                                    if processed <= 3:
                                        print(f"        + {val}")
                                except (InvalidOperation, ValueError, TypeError):
                                    pass

                print(f"     Total: {total} (from {processed} values)")
                return total

            # 5️⃣ CALCULATE PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get('plan')
            if plan_cfg:
                plan_column_id = plan_cfg.get('column_id')
                if plan_column_id:
                    plan_value = get_total_value(plan_column_id, reports, "PLAN")

            # 6️⃣ CALCULATE ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get('actual')
            if actual_cfg:
                actual_column_id = actual_cfg.get('column_id')
                if actual_column_id:
                    actual_value = get_total_value(actual_column_id, reports, "ACTUAL")

            # 7️⃣ ADD TO RESULT
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

            print(f"  ✅ RESULT: plan={plan_value}, actual={actual_value}")

        print("\n" + "=" * 80)
        print("FINAL SUMMARY:")
        for item in result:
            print(f"  {item['column_name'][:50]:50s} | {str(item['plan']):>10s} | {str(item['actual']):>10s}")
        print("=" * 80 + "\n")

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)