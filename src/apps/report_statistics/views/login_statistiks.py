from decimal import Decimal, InvalidOperation
from django.db.models import Q

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

            # 1️⃣ STATEMENT - name maydoni orqali qidirish (name_uz emas!)
            statement = Statement.objects.filter(
                Q(name=cfg["statement_name"]) | Q(name_uz=cfg["statement_name"])
            ).first()

            if not statement:
                print(f"❌ STATEMENT NOT FOUND: {cfg['statement_name']}")
                print("Available statements:", list(Statement.objects.values_list('name', 'name_uz')))
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
                print("❌ DEADLINE NOT FOUND")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue
            print("✅ DEADLINE:", deadline.id, "| submit_at:", deadline.submit_at)

            # 3️⃣ REPORTS - faqat ACCEPTED statusdagi reportlar
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,  # Faqat ACCEPTED
                is_report=True,
            )

            print("REPORT COUNT:", reports.count())
            if reports.count() == 0:
                print(f"⚠️ WARNING: No accepted reports found for {statement.name} and deadline {deadline.submit_at}")
                result.append({
                    "column_name": cfg["column_name"],
                    "unit": cfg["unit"],
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                })
                continue

            # 4️⃣ PLAN
            plan_value = Decimal("0")
            plan_cfg = cfg.get("plan")

            if plan_cfg:
                plan_column_id = plan_cfg["column_id"]
                print(f"PLAN COLUMN ID: {plan_column_id}")

                # StatementColumn mavjudligini tekshirish
                plan_column = StatementColumn.objects.filter(id=plan_column_id).first()
                if not plan_column:
                    print(f"⚠️ WARNING: Plan column {plan_column_id} not found")
                else:
                    print(f"✅ PLAN COLUMN: {plan_column.title}")

                    # ReportItem'larni olish
                    plan_items = ReportItem.objects.filter(
                        report__in=reports,
                        statement_column_id=plan_column_id
                    ).exclude(
                        Q(value__isnull=True) | Q(value='') | Q(value='None')
                    )

                    print(f"PLAN ITEMS COUNT: {plan_items.count()}")

                    # Qiymatlarni yig'ish
                    for item in plan_items:
                        try:
                            if item.value and item.value.strip():
                                val = Decimal(item.value.strip())
                                plan_value += val
                                print(f"  + Plan item value: {val}")
                        except (InvalidOperation, ValueError) as e:
                            print(f"⚠️ Invalid plan value: '{item.value}' - Error: {e}")
                            continue

                    print(f"TOTAL PLAN VALUE: {plan_value}")

            # 5️⃣ ACTUAL
            actual_value = Decimal("0")
            actual_cfg = cfg.get("actual")

            if actual_cfg:
                actual_column_id = actual_cfg["column_id"]
                print(f"ACTUAL COLUMN ID: {actual_column_id}")

                # StatementColumn mavjudligini tekshirish
                actual_column = StatementColumn.objects.filter(id=actual_column_id).first()
                if not actual_column:
                    print(f"⚠️ WARNING: Actual column {actual_column_id} not found")
                else:
                    print(f"✅ ACTUAL COLUMN: {actual_column.title}")

                    # ReportItem'larni olish
                    actual_items = ReportItem.objects.filter(
                        report__in=reports,
                        statement_column_id=actual_column_id
                    ).exclude(
                        Q(value__isnull=True) | Q(value='') | Q(value='None')
                    )

                    print(f"ACTUAL ITEMS COUNT: {actual_items.count()}")

                    # Qiymatlarni yig'ish
                    for item in actual_items:
                        try:
                            if item.value and item.value.strip():
                                val = Decimal(item.value.strip())
                                actual_value += val
                                print(f"  + Actual item value: {val}")
                        except (InvalidOperation, ValueError) as e:
                            print(f"⚠️ Invalid actual value: '{item.value}' - Error: {e}")
                            continue

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