import uuid, re
from uuid import UUID

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import serializers

from apps.general.models import Organization
from apps.reports.services.change_coma_to_dote import normalize_decimal_input_dote
from apps.utils.services import PeriodChoices
from apps.utils.translation import get_lang_code
from apps.base.serializers import CustomSerializer
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services.simple_ensure_plans import ensure_plant_plans_exist
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.reports.services.report_calculate_expressions import calculate_by_expressions


class PlantBasedReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
    source_report = serializers.UUIDField(required=False)
    inners = serializers.ListField(child=serializers.DictField())


class UniversalPlantReportCreateSerializer(CustomSerializer):
    """
    Universal serializer for creating all plant-based reports
    (Ko‘chat-ilovasi, Nihol-ilovasi, Urug‘ harakati, etc.)
    """
    deadline = serializers.UUIDField()
    report_items = PlantBasedReportItemSerializer(many=True)

    def validate(self, attrs):
        deadline_id = attrs["deadline"]
        user = self.context['request'].user
        organization = user.organization

        from apps.reports.models import Deadline
        try:
            deadline = Deadline.objects.select_related("statement").get(id=deadline_id)
        except Deadline.DoesNotExist:
            raise ValidationError({"deadline": "Berilgan deadline mavjud emas."})

        statement = deadline.statement
        submit_at = deadline.submit_at
        today = date.today()

        # ensure_plant_plans_exist(
        #     statement=statement,
        #     organization=organization
        # )

        # ✅ get_week_of_month funksiyasi
        def get_week_of_month(day):
            first_day = day.replace(day=1)
            adjusted_dom = day.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        # ✅ Deadline vaqt validatsiyasi
        if statement.period == PeriodChoices.KUNLIK:
            try:
                parts = submit_at.split("-")
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                report_day = date(year, month, day)
            except Exception:
                raise ValidationError({"submit_at": "Noto‘g‘ri sana formati. YYYY-MM-DD bo‘lishi kerak."})

            if report_day >= today:
                raise ValidationError({'submit_at': 'Faqat o‘tgan kunlar uchun topshirish mumkin.'})

            if report_day >= today:
                raise ValidationError({'submit_at': 'Faqat o‘tgan kunlar uchun topshirish mumkin.'})

        elif statement.period == PeriodChoices.HAFTALIK:
            match = re.match(r'^(?P<year>\d{4})-(?P<month>\d{2})-HAFTALIK_(?P<week>[1-4])$', submit_at)
            if not match:
                raise ValidationError({'submit_at': 'Noto‘g‘ri format. YYYY-MM-HAFTALIK_x bo‘lishi kerak.'})

            year = int(match.group('year'))
            month = int(match.group('month'))
            week = int(match.group('week'))

            if year > today.year or (year == today.year and month > today.month):
                raise ValidationError({'submit_at': 'Faqat o‘tgan haftalar uchun topshirish mumkin.'})
            if year == today.year and month == today.month and week >= get_week_of_month(today):
                raise ValidationError({'submit_at': 'Faqat o‘tgan haftalar uchun topshirish mumkin.'})

        elif statement.period == PeriodChoices.OYLIK:
            try:
                year, month = map(int, submit_at.split('-'))
            except Exception:
                raise ValidationError({'submit_at': 'Noto‘g‘ri oylik format. YYYY-MM bo‘lishi kerak.'})

            if year > today.year or (year == today.year and month >= today.month):
                raise ValidationError({'submit_at': 'Faqat o‘tgan oylar uchun topshirish mumkin.'})

        elif statement.period == PeriodChoices.CHORAKLIK:
            match = re.match(r'^(?P<year>\d{4})-CHORAK_(?P<quarter>[1-4])$', submit_at)
            if not match:
                raise ValidationError({'submit_at': 'Noto‘g‘ri chorak format. YYYY-CHORAK_x bo‘lishi kerak.'})

            year = int(match.group('year'))
            quarter = int(match.group('quarter'))
            current_quarter = (today.month - 1) // 3 + 1
            if year > today.year or (year == today.year and quarter >= current_quarter):
                raise ValidationError({'submit_at': 'Faqat o‘tgan choraklar uchun topshirish mumkin.'})

        elif statement.period == PeriodChoices.YILLIK:
            try:
                year = int(submit_at)
            except Exception:
                raise ValidationError({'submit_at': 'Noto‘g‘ri yillik format. YYYY bo‘lishi kerak.'})
            if year >= today.year:
                raise ValidationError({'submit_at': 'Faqat o‘tgan yillar uchun topshirish mumkin.'})

        # ✅ 5. Duplicated report borligini tekshir
        if Report.objects.filter(
            organization=user.organization,
            statement=statement,
            deadline=deadline,
            is_report=True
        ).exists():
            raise ValidationError({'report': 'Bu hisobot allaqachon mavjud.'})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data.pop("report_items")
        deadline_id = validated_data.get("deadline")
        foot_note = validated_data.get("foot_note")

        column_ids = [item["statement_column"] for item in items_data]
        columns = list(
            StatementColumn.objects
            .filter(id__in=column_ids)
            .only("id", "is_organization", "statement_id")
        )
        columns_map = {str(col.id): col for col in columns}

        # Buffers and mappings
        pending_items_map = {}  # (report_id, column_id) -> ReportItem (unsaved)
        inners_by_key = {}      # (report_id, column_id) -> list[dict(value, plant_id)]
        reports_map = {}        # (organization_id, statement_id) -> Report instance
        current_org = None

        # ✅ Plant ID larni oldindan tekshirib olamiz (FK xatosi bo'lmasligi uchun)
        plant_ids = set()
        for item in items_data:
            for inner in item.get("inners", []):
                pid = inner.get("plant")
                if pid:
                    try:
                        plant_ids.add(UUID(str(pid)))
                    except Exception:
                        raise serializers.ValidationError({
                            "plant": f"Noto'g'ri plant ID formati: {pid}"
                        })

        if plant_ids:
            existing = set(Plant.objects.filter(id__in=list(plant_ids)).values_list("id", flat=True))
            missing = [str(pid) for pid in plant_ids if pid not in existing]
            if missing:
                raise serializers.ValidationError({
                    "plant": f"Quyidagi plant ID(lar) topilmadi: {', '.join(missing)}"
                })

        with transaction.atomic():
            # 1) Build reports, pending ReportItems (without manual PKs) and cache inners per item-key
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError(f"Column {col_id} not found")

                inners = item.get("inners", [])

                # Organization column determines current organization and must not contain plant values
                if column.is_organization:
                    if any(inner.get("plant") for inner in inners):
                        raise serializers.ValidationError(
                            {"plant": "Tashkilotga oid ustunlarda plant yuborish taqiqlanadi."}
                        )

                    if not inners or not inners[0].get("value"):
                        raise serializers.ValidationError("Tashkilot ID kiritilishi kerak.")

                    org_id = inners[0]["value"]

                    # UUID format validation
                    try:
                        UUID(str(org_id))
                    except Exception:
                        raise serializers.ValidationError(f"Noto‘g‘ri tashkilot ID formati: {org_id}")

                    # Fetch organization
                    try:
                        current_org = Organization.objects.get(id=org_id)
                    except Organization.DoesNotExist:
                        raise serializers.ValidationError(f"Tashkilot topilmadi: {org_id}")

                    # Ensure report exists for (org, statement)
                    report_key = (current_org.id, column.statement.id)
                    if report_key not in reports_map:
                        reports_map[report_key] = Report.objects.create(
                            organization=current_org,
                            statement=column.statement,
                            deadline_id=deadline_id,
                            region=current_org.region,
                            status=Report.StatusChoices.SAVED,
                            is_plant_based=True,
                            created_by=user,
                            foot_note=foot_note,
                        )

                    report = reports_map[report_key]

                    # Prepare a pending ReportItem for the organization column
                    key = (report.id, column.id)
                    if key not in pending_items_map:
                        pending_items_map[key] = ReportItem(
                            report=report,
                            statement_column_id=column.id,
                        )

                    # Store the inner for organization (value only, no plant)
                    inners_by_key.setdefault(key, []).append({
                        "value": str(org_id),
                        "plant_id": None,
                    })
                    continue

                # For non-organization columns, ensure organization is determined
                if not current_org:
                    raise serializers.ValidationError(
                        "Tashkilot aniqlanmagan, iltimos 'Tashkilot nomi' columnni yuboring."
                    )

                # Ensure report exists for (org, statement)
                report_key = (current_org.id, column.statement.id)
                if report_key not in reports_map:
                    reports_map[report_key] = Report.objects.create(
                        organization=current_org,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        region=current_org.region,
                        status=Report.StatusChoices.SAVED,
                        is_plant_based=True,
                        created_by=user,
                        foot_note=foot_note,
                    )

                report = reports_map[report_key]

                # Prepare a pending ReportItem for this column
                key = (report.id, column.id)
                if key not in pending_items_map:
                    pending_items_map[key] = ReportItem(
                        report=report,
                        statement_column_id=column.id,
                    )

                # Normalize and cache inners for later save
                for inner in inners:
                    raw_value = inner.get("value")
                    normalize_value = normalize_decimal_input_dote(raw_value)
                    inners_by_key.setdefault(key, []).append({
                        "value": normalize_value,
                        "plant_id": inner.get("plant"),
                    })

            # 2) Persist ReportItems safely without manual PKs
            items_to_create = list(pending_items_map.values())
            if items_to_create:
                ReportItem.objects.bulk_create(items_to_create)

            # 3) Refetch items to build a reliable mapping (report_id, column_id) -> ReportItem
            # We only refetch for the keys we just created
            keys = list(pending_items_map.keys())
            if keys:
                report_ids = {rid for rid, _ in keys}
                column_ids_set = {cid for _, cid in keys}
                fetched_items = ReportItem.objects.filter(
                    report_id__in=report_ids,
                    statement_column_id__in=column_ids_set,
                )
                item_map = {
                    (ri.report_id, ri.statement_column_id): ri for ri in fetched_items
                }

                # Ensure all expected keys exist
                missing_keys = [k for k in keys if k not in item_map]
                if missing_keys:
                    raise serializers.ValidationError(
                        "ReportItem yaratishda xatolik yuz berdi (ba'zi ustunlar topilmadi)."
                    )

                # 4) Build ReportItemInner instances now that we have guaranteed ReportItems
                report_inners_buffer = []
                for key, inners_list in inners_by_key.items():
                    report_item = item_map[key]
                    for inner in inners_list:
                        report_inners_buffer.append(
                            ReportItemInner(
                                report_item=report_item,
                                plant_id=inner.get("plant_id"),
                                value=inner.get("value"),
                            )
                        )

                if report_inners_buffer:
                    ReportItemInner.objects.bulk_create(report_inners_buffer)

            # 5) Calculations on each report
            for report in reports_map.values():
                statement = report.statement
                if func := ALL_CALCULATORS.get(report.statement.name_uz):
                    func(report)
                elif statement.calculate_expression:
                    calculate_by_expressions(report)

                aggregate_individual_report(report)

        # ✅ Natija uchun instance
        self.instance = list(reports_map.values())
        return self.instance

    def to_representation(self, instance_list):
        lang = get_lang_code(self.context)
        serialized = []
        for report in instance_list:
            serialized.append(PlantReportListSerializer(
                report,
                context={"request": self.context.get("request")}
            ).data)
        return serialized
