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

        print("\n" + "=" * 80)
        print("QUERY PARAMS:")
        print(f"  monthly: {monthly}")
        print(f"  yearly: {yearly}")
        print("=" * 80)

        result = []

        for cfg in SUMMARY_CONFIG:
            print(f"\n{'=' * 80}")
            print(f"CONFIG: {cfg['column_name']}")
            print(f"  Statement Name: {cfg['statement_name']}")
            print(f"  Period: {cfg['period']}")
            print(f"  Plan Column ID: {cfg.get('plan', {}).get('column_id', 'N/A')}")
            print(f"  Actual Column ID: {cfg.get('actual', {}).get('column_id', 'N/A')}")
            print(f"{'=' * 80}")

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

            print(f"✅ Statement found:")
            print(f"   ID: {statement.id}")
            print(f"   Name: {statement.name}")
            print(f"   Name UZ: {getattr(statement, 'name_uz', 'N/A')}")

            # 2️⃣ DEADLINE
            deadline_qs = Deadline.objects.filter(statement=statement)

            print(f"\n🔍 Searching for deadline...")
            print(f"   Statement ID: {statement.id}")
            print(f"   Config period: {cfg['period']}")

            if cfg["period"] == "monthly":
                if monthly:
                    deadline_qs = deadline_qs.filter(submit_at=monthly)
                    print(f"   Filter: submit_at='{monthly}'")
                else:
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(
                        submit_len=7,
                        submit_at__contains='-'
                    ).exclude(
                        submit_at__contains='CHORAK'
                    ).order_by("-created_at")
                    print(f"   Filter: Latest monthly (len=7, has '-', no 'CHORAK')")

            elif cfg["period"] == "yearly":
                if yearly:
                    deadline_qs = deadline_qs.filter(submit_at=yearly)
                    print(f"   Filter: submit_at='{yearly}'")
                else:
                    from django.db.models.functions import Length
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(submit_len=4).order_by("-created_at")
                    print(f"   Filter: Latest yearly (len=4)")
            else:
                deadline_qs = deadline_qs.order_by("-created_at")
                print(f"   Filter: Latest (any)")

            # Debug: Show all available deadlines for this statement
            all_deadlines = Deadline.objects.filter(statement=statement).values('id', 'submit_at')
            print(f"\n   📋 All deadlines for this statement ({len(all_deadlines)}):")
            for d in all_deadlines[:5]:
                print(f"      - ID: {d['id']}, submit_at: {d['submit_at']}")
            if len(all_deadlines) > 5:
                print(f"      ... and {len(all_deadlines) - 5} more")

            deadline = deadline_qs.first()

            if not deadline:
                print("❌ DEADLINE NOT FOUND after filtering")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            print(f"✅ Deadline found:")
            print(f"   ID: {deadline.id}")
            print(f"   submit_at: {deadline.submit_at}")

            # 3️⃣ REPORTS
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
            )

            report_count = reports.count()
            print(f"\n📊 Searching for reports...")
            print(f"   Statement: {statement.id}")
            print(f"   Deadline: {deadline.id}")
            print(f"   Status: ACCEPTED")
            print(f"   Found: {report_count} reports")

            if report_count == 0:
                print("⚠️  No accepted reports found")

                # Debug: check if reports exist with different filters
                all_reports = Report.objects.filter(statement=statement, deadline=deadline)
                print(f"   📋 Reports for this statement+deadline (any status): {all_reports.count()}")
                for r in all_reports.values('id', 'status', 'organization__name')[:3]:
                    print(f"      - Report {r['id']}: status={r['status']}, org={r.get('organization__name', 'N/A')}")

                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            report_ids = list(reports.values_list('id', flat=True)[:10])
            print(f"   Report IDs: {report_ids}{' ...' if report_count > 10 else ''}")

            # 4️⃣ VALUE EXTRACTION
            def get_total_value(column_id, reports_qs):
                print(f"\n  {'—' * 40}")
                print(f"  🔍 Extracting values for column: {column_id}")

                # Check if column exists
                column_exists = StatementColumn.objects.filter(id=column_id).exists()
                if not column_exists:
                    print(f"  ❌ Column {column_id} does not exist in database!")
                    return Decimal("0")

                column_info = StatementColumn.objects.filter(id=column_id).values('id', 'title', 'title_uz',
                                                                                  'statement_id').first()
                print(f"  📋 Column info: {column_info}")

                # Get ReportItems
                report_items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                item_count = report_items.count()
                print(f"  📝 ReportItems found: {item_count}")

                if item_count == 0:
                    print(f"  ⚠️  No ReportItems for this column")

                    # Debug: Show what columns DO exist for these reports
                    existing_columns = ReportItem.objects.filter(
                        report__in=reports_qs
                    ).values_list('statement_column_id', flat=True).distinct()[:10]
                    print(f"  📋 Columns that DO exist in these reports: {list(existing_columns)}")

                    return Decimal("0")

                # Show sample ReportItems
                sample_items = report_items.values('id', 'report_id', 'value')[:3]
                print(f"  📄 Sample ReportItems:")
                for item in sample_items:
                    print(f"     - ID: {item['id']}, Report: {item['report_id']}, Value: {item['value']}")

                # Get ReportItemInners
                inners = ReportItemInner.objects.filter(
                    report_item__in=report_items
                )

                inner_count = inners.count()
                print(f"  📦 ReportItemInners found: {inner_count}")

                total = Decimal("0")
                processed_count = 0
                skipped_count = 0

                if inner_count > 0:
                    # Sum from inners
                    print(f"  🔢 Processing inner values...")
                    for inner in inners:
                        if inner.value:
                            value_str = str(inner.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                    processed_count += 1
                                    if processed_count <= 5:  # Show first 5
                                        print(f"     + {val}")
                                except (InvalidOperation, ValueError, TypeError) as e:
                                    skipped_count += 1
                                    print(f"     ⚠️  Skipped invalid: '{inner.value}' ({e})")
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1

                    if processed_count > 5:
                        print(f"     ... and {processed_count - 5} more values")
                else:
                    # Fallback to ReportItem.value
                    print(f"  ℹ️  No inners, using ReportItem.value...")
                    for item in report_items:
                        if item.value:
                            value_str = str(item.value).strip()
                            if value_str and value_str not in ['', 'None', 'null']:
                                try:
                                    val = Decimal(value_str)
                                    total += val
                                    processed_count += 1
                                    if processed_count <= 5:
                                        print(f"     + {val}")
                                except (InvalidOperation, ValueError, TypeError) as e:
                                    skipped_count += 1
                                    print(f"     ⚠️  Skipped invalid: '{item.value}' ({e})")
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1

                print(f"  ✅ Processed: {processed_count}, Skipped: {skipped_count}")
                print(f"  💰 TOTAL: {total}")
                print(f"  {'—' * 40}")
                return total

            # 5️⃣ CALCULATE PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")

            if plan_cfg:
                plan_column_id = plan_cfg["column_id"]
                print(f"\n📋 PROCESSING PLAN")
                print(f"   Column ID: {plan_column_id}")
                plan_value = get_total_value(plan_column_id, reports)

            # 6️⃣ CALCULATE ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")

            if actual_cfg:
                actual_column_id = actual_cfg["column_id"]
                print(f"\n📋 PROCESSING ACTUAL")
                print(f"   Column ID: {actual_column_id}")
                actual_value = get_total_value(actual_column_id, reports)

            # 7️⃣ ADD TO RESULT
            result.append({
                "column_name": cfg["column_name"],
                "unit": cfg["unit"],
                "plan": plan_value,
                "actual": actual_value,
            })

            print(f"\n✅ FINAL RESULT FOR THIS CONFIG:")
            print(f"   Plan: {plan_value}")
            print(f"   Actual: {actual_value}")

        print("\n" + "=" * 80)
        print("SUMMARY OF ALL RESULTS:")
        print("=" * 80)
        for item in result:
            print(
                f"{item['column_name'][:50]:50s} | Plan: {str(item['plan']):>12s} | Actual: {str(item['actual']):>12s}")
        print("=" * 80 + "\n")

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)