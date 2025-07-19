

def get_leaf_columns_under_ilova_root(root):
    """
    Root (ilova) ostidagi barcha leaf-columnlarni (va is_organization=False bo‘lganlarini) optimized queryset sifatida qaytaradi.
    Faqat root`ning bevosita farzandlaridan pastdagilar (2-daraja va chuqurroq) olinadi.
    """

    return (
        StatementColumn.objects.filter(
            statement=root.statement,
            is_organization=False,
            children__isnull=True,
        ).select_related('parent').prefetch_related('children')
    )

# ===================================== plant_repot.py

from django.db import models
from apps.reports.models import StatementColumn, Report, ReportItem, ColumnPlant
from apps.reports.services.get_leaf_columns import get_leaf_columns_under_ilova_root
from apps.utils.translation import get_lang_code, get_translated_field


def get_or_create_report_and_columns(deadline, organization, ilova_title_uz: str, context=None):
    lang = get_lang_code(context) if context else "uz"

    report, created = Report.objects.get_or_create(
        deadline=deadline,
        organization=organization,
        statement=deadline.statement,
        defaults={"status": Report.StatusChoices.SAVED},
    )

    try:
        ilova_root = StatementColumn.objects.get(
            statement=deadline.statement,
            title_uz__iexact=ilova_title_uz,
            parent__isnull=True
        )
    except StatementColumn.DoesNotExist:
        return report, []

    if not created:
        existing_items = ReportItem.objects.filter(
            report=report,
            statement_column__in=StatementColumn.objects.filter(statement=deadline.statement)
        ).select_related("statement_column", "plant")

        result = {}
        for item in existing_items:
            col_id = str(item.statement_column_id)
            if col_id not in result:
                result[col_id] = {
                    "statement_column_id": col_id,
                    "statement_column_name": item.statement_column.title_uz,
                    "plant_values": [] if item.plant_id else None,
                    "value": None
                }

            if item.plant_id:
                result[col_id]["plant_values"].append({
                    "plant_id": str(item.plant_id),
                    "plant_name": get_translated_field(item.plant, "name", lang),
                    "value": item.value
                })
            else:
                result[col_id]["value"] = get_translated_field(organization, "name", lang)

        return report, list(result.values())

    # ➤ Get all leaf columns under ilova_root (excludes is_organization=True)
    leaf_columns = get_leaf_columns_under_ilova_root(ilova_root).prefetch_related(
        models.Prefetch(
            'column_plants',
            queryset=ColumnPlant.objects.select_related('plant').order_by('ordering')
        )
    )

    items_to_create = []
    result = []

    # ➤ Add plant-based columns
    for column in leaf_columns:
        column_plants = column.column_plants.all()
        if not column_plants:
            continue

        plant_values = []
        for cp in column_plants:
            items_to_create.append(ReportItem(
                report=report,
                statement_column=column,
                plant=cp.plant,
                value=None
            ))
            plant_values.append({
                "plant_id": str(cp.plant.id),
                "plant_name": get_translated_field(cp.plant, "name", lang),
                "value": None
            })

        result.append({
            "statement_column_id": str(column.id),
            "statement_column_name": column.title_uz,
            "plant_values": plant_values
        })

    # ➤ Add is_organization=True column (e.g. "Ташкилот номи")
    org_columns = StatementColumn.objects.filter(
        parent__in=StatementColumn.objects.filter(parent=ilova_root),
        is_organization=True
    )

    for column in org_columns:
        items_to_create.append(ReportItem(
            report=report,
            statement_column=column,
            plant=None,
            value=organization.id  # saqlash uchun ID
        ))

        result.append({
            "statement_column_id": str(column.id),
            "statement_column_name": column.title_uz,
            "value": get_translated_field(organization, "name", lang)
        })

    # Save all report items
    ReportItem.objects.bulk_create(items_to_create)

    return report, result

# =========================================== get_report_items

from rest_framework import serializers
from apps.reports.models import Report,ReportItem
from apps.reports.serializers import ReportItemSerializer, ReportItemPlantValueSerializer
from apps.utils.translation import get_lang_code, get_translated_field


from rest_framework import serializers
from apps.reports.models import Report
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

    def get_report_items(self, obj):
        items = obj.report_items.all().select_related(
            'statement_column', 'plant', 'statement_column__parent'
        )
        lang = get_lang_code(self.context)

        # 1. Bu Ko‘chat yoki Nihol reportimi?
        statement_name_uz = get_translated_field(obj.statement, "name", lang)
        is_kochat_or_nihol_statement = statement_name_uz.strip() == "Ko‘chat va Nihol"

        # 2. Plant borligini tekshiramiz
        plant_items = items.filter(plant__isnull=False)

        if is_kochat_or_nihol_statement and plant_items.exists():
            # Bu Ko‘chat yoki Nihol reporti, plant_values formatda chiqaramiz
            result = {}
            for item in plant_items:
                col_id = str(item.statement_column_id)
                if col_id not in result:
                    result[col_id] = {
                        "statement_column_id": col_id,
                        "statement_column_name": item.statement_column.title_uz,
                        "plant_values": [],
                    }

                result[col_id]["plant_values"].append({
                    "plant_id": str(item.plant_id),
                    "plant_name": get_translated_field(item.plant, "name", lang),
                    "value": item.value
                })
            return list(result.values())

        # Aks holda oddiy formatda (value bilan)
        from collections import OrderedDict
        org_groups = OrderedDict()
        current_group = []
        last_org_col_id = None

        for item in items.order_by('id'):
            if item.statement_column.is_organization:
                last_org_col_id = str(item.statement_column_id)
                current_group = []
                org_groups[last_org_col_id] = current_group

            if last_org_col_id is None:
                last_org_col_id = 'default'
                org_groups[last_org_col_id] = current_group

            current_group.append(item)

        result = []
        for group_items in org_groups.values():
            for item in group_items:
                col = item.statement_column
                result.append({
                    "statement_column_id": str(col.id),
                    "statement_column_name": col.title_uz,
                    "value": (
                        get_translated_field(obj.organization, "name", lang)
                        if col.is_organization else item.value
                    )
                })

        return result