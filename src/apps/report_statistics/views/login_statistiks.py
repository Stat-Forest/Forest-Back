from decimal import Decimal, InvalidOperation
from django.db.models import Q
from django.db.models.functions import Length

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import Report, ReportItem, ReportItemInner, Statement, StatementColumn, Deadline
from apps.report_statistics.serializers import ReportSummarySerializer
from apps.report_statistics.summary_config import SUMMARY_CONFIG

# Statement constants
MONTHLY_STATEMENTS = [
    "Dorivor yetishtirish",
    "O'rmon barpo qilish bo'limi",
    "Ko'chatxona va Niholxona Jami",
    "Tut Ko'chat va Tut Nihol"
]

YEARLY_STATEMENTS = [
    "O'rmon bilan qoplangan yerlar",
    "Yer o'zlashtirish"
]


class ReportLoginSummaryAPIView(APIView):
    @extend_schema(
        tags=["Login Stats"],
        parameters=[
            OpenApiParameter(
                name="monthly",
                type=OpenApiTypes.STR,
                required=False,
                description="Oylik davr: YYYY-MM (agar berilmasa, oxirgi oylik deadline)"
            ),
            OpenApiParameter(
                name="yearly",
                type=OpenApiTypes.STR,
                required=False,
                description="Yillik davr: YYYY (agar berilmasa, oxirgi yillik deadline)"
            ),
            OpenApiParameter(
                name="statement_status",
                type=OpenApiTypes.STR,
                required=False,
                description="Statement turi: year yoki month (default: hammasi)",
                enum=["year", "month"]
            ),
            OpenApiParameter(
                name="lang",
                type=OpenApiTypes.STR,
                required=False,
                description="Til: uz yoki ru (default: uz)",
                enum=["uz", "ru"]
            ),
        ]
    )
    def get(self, request):
        monthly = request.query_params.get("monthly")
        yearly = request.query_params.get("yearly")
        statement_status = request.query_params.get("statement_status")
        lang = request.query_params.get("lang", "uz")

        print("\n" + "=" * 80)
        print(f"REQUEST PARAMS: monthly={monthly}, yearly={yearly}, statement_status={statement_status}, lang={lang}")
        print("=" * 80)

        result = []

        # Config'ni filter qilish
        filtered_config = SUMMARY_CONFIG
        if statement_status:
            if statement_status == "year":
                filtered_config = [cfg for cfg in SUMMARY_CONFIG if cfg["period"] == "yearly"]
                print(f"📋 Filtering: Only YEARLY statements ({len(filtered_config)} items)")
            elif statement_status == "month":
                filtered_config = [cfg for cfg in SUMMARY_CONFIG if cfg["period"] == "monthly"]
                print(f"📋 Filtering: Only MONTHLY statements ({len(filtered_config)} items)")

        for cfg in filtered_config:
            print(f"\n{'=' * 80}")
            print(f"CONFIG: {cfg['column_name']}")
            print(f"  statement_name: {cfg['statement_name']}")
            print(f"  period: {cfg['period']}")

            # 1️⃣ STATEMENT (name_uz orqali qidirish)
            statement = Statement.objects.filter(
                Q(name_uz=cfg["statement_name"]) |
                Q(name_uz__iexact=cfg["statement_name"])
            ).first()

            if not statement:
                print(f"  ❌ STATEMENT NOT FOUND")
                result.append({
                    "column_name": self._get_translated_text(cfg.get('column_name_uz'), cfg.get('column_name_ru'), lang,
                                                             cfg['column_name']),
                    "unit": self._get_translated_text(cfg.get('unit_uz'), cfg.get('unit_ru'), lang, cfg['unit']),
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                    "percentage": Decimal("0"),
                    "status": self._get_translated_text("Bajarilmadi", "Не выполнено", lang),
                })
                continue

            print(f"  ✅ STATEMENT FOUND: id={statement.id}, name_uz={statement.name_uz}")

            # 2️⃣ DEADLINE (period bo'yicha avtomatik aniqlash)
            config_period = cfg["period"]

            # Statementni period bo'yicha tekshirish
            is_monthly_statement = statement.name_uz in MONTHLY_STATEMENTS
            is_yearly_statement = statement.name_uz in YEARLY_STATEMENTS

            print(f"  🔍 Statement type: monthly={is_monthly_statement}, yearly={is_yearly_statement}")

            deadline_qs = Deadline.objects.filter(statement=statement)

            # Agar parametr berilgan bo'lsa, uni ishlatish
            if monthly and is_monthly_statement:
                print(f"  📅 Using monthly parameter: {monthly}")
                deadline_qs = deadline_qs.filter(submit_at=monthly)
            elif yearly and is_yearly_statement:
                print(f"  📅 Using yearly parameter: {yearly}")
                deadline_qs = deadline_qs.filter(submit_at=yearly)
            else:
                # Parametr yo'q - oxirgi deadlineni olish
                if is_monthly_statement or config_period == "monthly":
                    print(f"  📅 Using latest monthly deadline")
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(
                        submit_len=7,
                        submit_at__contains='-'
                    ).exclude(
                        submit_at__icontains='CHORAK'
                    ).order_by("-submit_at", "-created_at")

                elif is_yearly_statement or config_period == "yearly":
                    print(f"  📅 Using latest yearly deadline")
                    deadline_qs = deadline_qs.annotate(
                        submit_len=Length('submit_at')
                    ).filter(submit_len=4).order_by("-submit_at", "-created_at")
                else:
                    print(f"  📅 Using latest deadline (any period)")
                    deadline_qs = deadline_qs.order_by("-created_at")

            # Available deadlines
            all_deadlines = list(Deadline.objects.filter(statement=statement).values('id', 'submit_at')[:10])
            print(f"  📋 Available deadlines: {[d['submit_at'] for d in all_deadlines]}")

            deadline = deadline_qs.first()

            if not deadline:
                print(f"  ❌ DEADLINE NOT FOUND")
                result.append({
                    "column_name": self._get_translated_text(cfg.get('column_name_uz'), cfg.get('column_name_ru'), lang,
                                                             cfg['column_name']),
                    "unit": self._get_translated_text(cfg.get('unit_uz'), cfg.get('unit_ru'), lang, cfg['unit']),
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                    "percentage": Decimal("0"),
                    "status": self._get_translated_text("Bajarilmadi", "Не выполнено", lang),
                })
                continue

            print(f"  ✅ DEADLINE FOUND: id={deadline.id}, submit_at={deadline.submit_at}")

            # 3️⃣ REPORTS (faqat ACCEPTED)
            reports = Report.objects.filter(
                statement=statement,
                deadline=deadline,
                status=Report.StatusChoices.ACCEPTED,
                is_report=True,
            )

            report_count = reports.count()
            print(f"  📊 REPORTS: {report_count} accepted reports found")

            if report_count == 0:
                print(f"  ⚠️  No accepted reports, returning 0")
                result.append({
                    "column_name": self._get_translated_text(cfg.get('column_name_uz'), cfg.get('column_name_ru'), lang,
                                                             cfg['column_name']),
                    "unit": self._get_translated_text(cfg.get('unit_uz'), cfg.get('unit_ru'), lang, cfg['unit']),
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                    "percentage": Decimal("0"),
                    "status": self._get_translated_text("Bajarilmadi", "Не выполнено", lang),
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
                print(f"     Column: {col_info.get('title_uz', 'N/A')}")

                # Get ReportItems
                report_items = ReportItem.objects.filter(
                    report__in=reports_qs,
                    statement_column_id=column_id
                )

                item_count = report_items.count()
                print(f"     ReportItems: {item_count}")

                if item_count == 0:
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

            # 7️⃣ CALCULATE PERCENTAGE & STATUS
            percentage = Decimal("0")
            status = self._get_translated_text("Bajarilmadi", "Не выполнено", lang)

            if plan_value > 0:
                percentage = round((actual_value / plan_value) * 100, 2)
                if percentage >= 100:
                    status = self._get_translated_text("Bajarildi", "Выполнено", lang)
                else:
                    status = self._get_translated_text("Bajarilmadi", "Не выполнено", lang)
            elif actual_value > 0:
                # Plan yo'q lekin actual bor
                percentage = Decimal("100")
                status = self._get_translated_text("Bajarildi", "Выполнено", lang)

            # 8️⃣ ADD TO RESULT
            result.append({
                "column_name": self._get_translated_text(cfg.get('column_name_uz'), cfg.get('column_name_ru'), lang,
                                                         cfg['column_name']),
                "unit": self._get_translated_text(cfg.get('unit_uz'), cfg.get('unit_ru'), lang, cfg['unit']),
                "plan": plan_value,
                "actual": actual_value,
                "percentage": percentage,
                "status": status,
            })

            print(f"  ✅ RESULT: plan={plan_value}, actual={actual_value}, percentage={percentage}%, status={status}")

        print("\n" + "=" * 80)
        print("FINAL SUMMARY:")
        for item in result:
            print(
                f"  {item['column_name'][:40]:40s} | Plan: {str(item['plan']):>10s} | Actual: {str(item['actual']):>10s} | {str(item['percentage']):>6s}% | {item['status']}")
        print("=" * 80 + "\n")

        serializer = ReportSummarySerializer(result, many=True)
        return Response(serializer.data)

    def _get_translated_text(self, uz_text, ru_text, lang, default=None):
        """Til bo'yicha tarjima qaytarish"""
        if lang == "ru" and ru_text:
            return ru_text
        elif uz_text:
            return uz_text
        elif default:
            return default
        return uz_text or ru_text or ""