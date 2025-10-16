import uuid, re
from datetime import date
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from apps.general.models import Organization
from apps.utils.services import PeriodChoices
from apps.utils.translation import get_lang_code
from apps.base.serializers import CustomSerializer
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.reports.services.individual_general_report import aggregate_individual_report


class PlantBasedReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
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
        report_items = attrs['report_items']
        user = self.context['request'].user

        from apps.reports.models import Deadline
        try:
            deadline = Deadline.objects.select_related("statement").get(id=deadline_id)
        except Deadline.DoesNotExist:
            raise ValidationError({"deadline": "Berilgan deadline mavjud emas."})

        statement = deadline.statement
        submit_at = deadline.submit_at
        today = date.today()

        # ✅ get_week_of_month funksiyasi
        def get_week_of_month(day):
            first_day = day.replace(day=1)
            adjusted_dom = day.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        # ✅ Deadline vaqt validatsiyasi
        if statement.period == PeriodChoices.KUNLIK:
            report_day = date.fromisoformat(submit_at)
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
        items_data = validated_data.pop("report_items")
        deadline_id = validated_data.get("deadline")

        column_ids = [item["statement_column"] for item in items_data]
        columns = StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        columns_map = {str(col.id): col for col in columns}

        report_items_buffer = []
        report_inners_buffer = []
        reports_map = {}
        current_org = None

        with transaction.atomic():
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError(f"Column {col_id} not found")

                inners = item.get("inners", [])

                # ✅ 1. "Tashkilot nomi" column -> org_id dan tashkilotni aniqlash
                if column.is_organization:
                    if not inners or not inners[0].get("value"):
                        raise serializers.ValidationError("Tashkilot ID kiritilishi kerak.")

                    org_id = inners[0]["value"]

                    # UUID formatini tekshirish
                    try:
                        UUID(str(org_id))
                    except Exception:
                        raise serializers.ValidationError(f"Noto‘g‘ri tashkilot ID formati: {org_id}")

                    # Tashkilotni olish
                    try:
                        current_org = Organization.objects.get(id=org_id)
                    except Organization.DoesNotExist:
                        raise serializers.ValidationError(f"Tashkilot topilmadi: {org_id}")

                    # ✅ Report yaratamiz
                    report_key = (current_org.id, column.statement.id)
                    if report_key not in reports_map:
                        report = Report.objects.create(
                            organization=current_org,
                            statement=column.statement,
                            deadline_id=deadline_id,
                            region=current_org.region,
                            status=Report.StatusChoices.SAVED,
                            is_plant_based=True,
                        )
                        reports_map[report_key] = report

                    report = reports_map[report_key]
                    report_item_id = uuid.uuid4()

                    # ✅ Tashkilot column uchun ham ReportItem saqlanadi
                    report_items_buffer.append(
                        ReportItem(
                            id=report_item_id,
                            report=report,
                            statement_column=column
                        )
                    )

                    # ✅ va ichiga organization_id (UUID) saqlaymiz
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            value=str(org_id)
                        )
                    )
                    continue

                # ✅ 2. Org aniqlanmagan bo‘lsa xato
                if not current_org:
                    raise serializers.ValidationError(
                        "Tashkilot aniqlanmagan, iltimos 'Tashkilot nomi' columnni yuboring."
                    )

                # ✅ 3. Reportni yaratamiz yoki olamiz
                report_key = (current_org.id, column.statement.id)
                if report_key not in reports_map:
                    report = Report.objects.create(
                        organization=current_org,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        region=current_org.region,
                        status=Report.StatusChoices.SAVED,
                        is_plant_based=True,
                    )
                    reports_map[report_key] = report

                report = reports_map[report_key]
                report_item_id = uuid.uuid4()

                # ✅ Oddiy ReportItem
                report_items_buffer.append(
                    ReportItem(
                        id=report_item_id,
                        report=report,
                        statement_column=column
                    )
                )

                # ✅ Plant innerlar
                for inner in inners:
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            plant_id=inner.get("plant"),
                            value=inner.get("value")
                        )
                    )

            # Bulk create
            ReportItem.objects.bulk_create(report_items_buffer)
            ReportItemInner.objects.bulk_create(report_inners_buffer)

            # ✅ Hisob-kitob
            for report in reports_map.values():
                if func := ALL_CALCULATORS.get(report.statement.name_uz):
                    func(report)
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
