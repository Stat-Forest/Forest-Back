import re

from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


def get_or_create_general_report(statement, deadline, region=None):
    general_report, _ = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_general": True
        }
    )

    if region:
        # General reportga hududiy belgini saqlash (optional)
        general_report.sent_by_role = f"region:{region}"
        general_report.save(update_fields=["sent_by_role"])

    return general_report


def is_number(value: str) -> bool:
    if value is None:
        return False
    return re.match(r'^\d+(\.\d+)?$', str(value)) is not None


def aggregate_general_report(statement, deadline):
    # 1️⃣ Oddiy (general emas) reportlarni olamiz
    reports = Report.objects.filter(
        statement=statement,
        deadline=deadline,
        is_general=False
    )

    if not reports.exists():
        return None

    # Viloyatni olish → birinchi tashkilotdan
    any_report = reports.first()
    region = any_report.organization.region if any_report.organization else None

    # 2️⃣ Barcha report_items
    all_items = ReportItem.objects.filter(report__in=reports).prefetch_related("inners")

    # 3️⃣ General reportni olish yoki yaratish
    general_report, created = Report.objects.get_or_create(
        organization=None,
        statement=statement,
        deadline=deadline,
        defaults={
            "status": Report.StatusChoices.SAVED,
            "is_general": True,
            "region": region,   # ✅ yangi report yaratilsa, region yozib qo‘yamiz
        }
    )

    # ✅ Agar general report oldin yaratilgan bo‘lsa ham regionni yangilaymiz
    if general_report.region != region:
        general_report.region = region
        general_report.save(update_fields=["region"])

    # Eski itemlarni tozalaymiz
    ReportItem.objects.filter(report=general_report).delete()

    # 4️⃣ Column bo‘yicha guruhlash
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in all_items:
        for inner in item.inners.all():
            grouped[item.statement_column_id].append(inner.value)

    new_items = []
    new_inners = []

    for column_id, values in grouped.items():
        first_value = values[0] if values else None

        report_item = ReportItem(
            report=general_report,
            statement_column_id=column_id
        )
        new_items.append(report_item)

        if is_number(first_value):
            total = sum(float(v) for v in values if is_number(v))
            new_inners.append(
                ReportItemInner(report_item=report_item, value=str(total))
            )
        else:
            for v in values:
                new_inners.append(
                    ReportItemInner(report_item=report_item, value=v)
                )

    # 5️⃣ Bulk yaratish
    ReportItem.objects.bulk_create(new_items)
    ReportItemInner.objects.bulk_create(new_inners)

    return general_report


# ============================== CREATE REPORT

import uuid

from django.db import transaction
from rest_framework import serializers

from apps.general.models import Organization
from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
from apps.reports.services.general_report import aggregate_general_report
from apps.utils.translation import get_lang_code, get_translated_field


class ReportItemInnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItemInner
        fields = ["id", "value"]


class ReportItemSerializer(serializers.ModelSerializer):
    inners = ReportItemInnerSerializer(many=True)

    class Meta:
        model = ReportItem
        fields = ["statement_column", "inners"]


class ReportCreateSerializer(serializers.ModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "deadline",
            "report_items"
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("report_items")
        deadline = validated_data["deadline"]

        # columnlarni oldindan map qilamiz
        column_ids = [item["statement_column"] for item in items_data]
        columns_map = {
            str(c.id): c
            for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        }

        reports_map = {}
        current_org_id = None

        # ✅ Hamma narsani bufferga yig‘amiz
        report_items_buffer = []  # bu ReportItem bulk_create uchun
        report_inners_buffer = []  # bu ReportItemInner bulk_create uchun

        with transaction.atomic():
            for item in items_data:
                col_id = item["statement_column"]
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})

                inners_data = item.get("inners", [])

                # 1️⃣ ORGANIZATION BLOKI
                if column.is_organization:
                    if not inners_data or "value" not in inners_data[0]:
                        raise serializers.ValidationError(
                            {"detail": f"Organization inners required for column {col_id}"}
                        )
                    current_org_id = inners_data[0]["value"]

                    # bu orgga tegishli report
                    report_key = (current_org_id, str(column.statement.id))
                    if report_key not in reports_map:
                        org_instance = Organization.objects.get(id=current_org_id)
                        report, _ = Report.objects.get_or_create(
                            organization=org_instance,
                            statement=column.statement,
                            deadline=deadline,
                            defaults={"status": Report.StatusChoices.SAVED}
                        )
                        reports_map[report_key] = report

                    report = reports_map[report_key]

                    # ✅ ReportItem ni bufferga qo‘shamiz
                    report_item_id = uuid.uuid4()
                    report_items_buffer.append(
                        ReportItem(
                            id=report_item_id,
                            report=report,
                            statement_column=column
                        )
                    )
                    # Organization column inners
                    for inner in inners_data:
                        report_inners_buffer.append(
                            ReportItemInner(
                                report_item_id=report_item_id,
                                value=inner["value"]
                            )
                        )
                    continue

                # 2️⃣ Oddiy columnlar
                if not current_org_id:
                    raise serializers.ValidationError({"detail": "Organization column required before data columns"})

                child_statement = column.statement
                report_key = (current_org_id, str(child_statement.id))
                if report_key not in reports_map:
                    org_instance = Organization.objects.get(id=current_org_id)
                    report, _ = Report.objects.get_or_create(
                        organization=org_instance,
                        statement=child_statement,
                        deadline=deadline,
                        defaults={"status": Report.StatusChoices.SAVED}
                    )
                    reports_map[report_key] = report

                report = reports_map[report_key]

                # ✅ ReportItem ni bufferga qo‘shamiz
                report_item_id = uuid.uuid4()
                report_items_buffer.append(
                    ReportItem(
                        id=report_item_id,
                        report=report,
                        statement_column=column
                    )
                )
                # bu columnning barcha inners’larini bufferga qo‘shamiz
                for inner in inners_data:
                    report_inners_buffer.append(
                        ReportItemInner(
                            report_item_id=report_item_id,
                            value=inner["value"]
                        )
                    )

            # ✅ Endi 1 marta DB query bilan bulk_create qilamiz
            ReportItem.objects.bulk_create(report_items_buffer, batch_size=1000)
            ReportItemInner.objects.bulk_create(report_inners_buffer, batch_size=2000)

            # ✅ General reportni yangilaymiz (faqat 1 marta)
            if reports_map:
                # barcha reportlar bitta statement bo‘yicha bo‘ladi
                any_report = list(reports_map.values())[0]
                aggregate_general_report(any_report.statement, deadline)

        return Report.objects.filter(id__in=[r.id for r in reports_map.values()])


    # ============================ LIST REPORT

    from rest_framework import serializers
    from apps.reports.models import Report, StatementColumn
    from apps.utils.services.general_values import build_columns_with_jami
    from apps.utils.translation import get_lang_code, get_translated_field

    class ReportListSerializer(serializers.ModelSerializer):
        period = serializers.CharField(source='statement.period')
        organization_name = serializers.SerializerMethodField()
        report_items = serializers.SerializerMethodField()
        statement_name = serializers.SerializerMethodField()
        sent_by_full_name = serializers.SerializerMethodField()
        sent_by_org_name = serializers.SerializerMethodField()

        class Meta:
            model = Report
            fields = (
                'id', 'organization', 'organization_name',
                'statement', 'statement_name',
                'deadline', 'period', 'status',
                'created_at', 'cancel_reason',
                'cancelled_at', 'sent_at', 'accepted_at',
                'report_items',
                'sent_by_full_name', 'sent_by_org_name', 'sent_by_role',
            )

        def get_organization_name(self, obj):
            lang = get_lang_code(self.context)
            return get_translated_field(obj.organization, "name", lang)

        def get_statement_name(self, obj):
            lang = get_lang_code(self.context)
            return get_translated_field(obj.statement, "name", lang)

        def get_sent_by_full_name(self, obj):
            if obj.sent_by:
                return obj.sent_by.full_name
            return None

        def get_sent_by_org_name(self, obj):
            lang = get_lang_code(self.context)
            if obj.sent_by_org:
                return get_translated_field(obj.sent_by_org, "name", lang)
            return None

        def get_report_items(self, report):
            lang = get_lang_code(self.context)
            # ❗️ Bunda inner so‘rov ketmaydi, chunki oldindan prefetch bo‘lgan
            items = report.report_items.all()

            if report.is_general:
                organization_id = "general"
                organization_name = "Barcha tashkilotlar bo‘yicha umumiy"

                org_qs = Report.objects.filter(
                    statement=report.statement,
                    deadline=report.deadline,
                    is_general=False
                ).values("organization_id", "organization__name").distinct()

                org_inners = [
                    {"id": str(o["organization_id"]), "value": o["organization__name"] or ""}
                    for o in org_qs
                ]

                org_column = StatementColumn.objects.filter(
                    statement=report.statement,
                    is_organization=True
                ).first()

                org_column_json = {
                    "statement_column_id": str(org_column.id),
                    "statement_column_name": get_translated_field(org_column, "title", lang),
                    "inners": org_inners
                }

                other_columns = []
                for item in items:
                    if item.statement_column.is_organization:
                        continue
                    other_columns.append({
                        "statement_column_id": str(item.statement_column.id),
                        "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                        # ❗️ Bu yerda endi query bo‘lmaydi
                        "inners": [
                            {"id": str(inner.id), "value": inner.value}
                            for inner in item.inners.all()
                        ]
                    })

                return [{
                    "organization_id": organization_id,
                    "organization_name": organization_name,
                    "statement_columns": [org_column_json] + other_columns
                }]
            else:
                return [{
                    "organization_id": str(report.organization.id),
                    "organization_name": report.organization.name,
                    "statement_columns": [
                        {
                            "statement_column_id": str(item.statement_column.id),
                            "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                            # ❗️ Bu yerda ham query bo‘lmaydi
                            "inners": [
                                {"id": str(inner.id), "value": inner.value}
                                for inner in item.inners.all()
                            ]
                        }
                        for item in items
                    ]
                }]

