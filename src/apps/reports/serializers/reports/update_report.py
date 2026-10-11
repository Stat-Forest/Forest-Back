from django.db import transaction

from rest_framework import serializers

from apps.base.serializers import CustomModelSerializer
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.services import aggregate_individual_report
from apps.reports.calculate_orderings.calculated_columns import CALCULATED_COLUMNS
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn


class ReportItemInnerSerializer(CustomModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ReportItemInner
        fields = ["id", "value"]

    def get_value(self, obj):
        # Avoid accessing obj.report_item.statement_column which can trigger N+1.
        # We rely on a precomputed map in context: is_org_by_item_id.
        is_org_map = self.context.get("is_org_by_item_id", {})
        report_item_id = self.context.get("report_item_id") or getattr(obj, "report_item_id", None)
        if report_item_id is not None and is_org_map.get(str(report_item_id)):
            return str(obj.value)
        return obj.value


class ReportItemUpdateSerializer(serializers.ModelSerializer):
    inners = serializers.SerializerMethodField()

    class Meta:
        model = ReportItem
        fields = ["statement_column", "inners"]

    def get_inners(self, obj):
        # Pass report_item_id in context so inner serializer never dereferences FKs
        ctx = dict(self.context)
        ctx["report_item_id"] = str(obj.id)
        return ReportItemInnerSerializer(obj.inners.all(), many=True, context=ctx).data


class ReportUpdateSerializer(serializers.ModelSerializer):
    report_items = serializers.ListField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "deadline",
            "report_items"
        ]

    def update(self, instance, validated_data):
        items_data = validated_data.pop("report_items")

        if instance.status == Report.StatusChoices.CANCELLED:
            instance.status = Report.StatusChoices.SAVED
            instance.cancel_reason = None
            instance.cancelled_at = None
            instance.save(update_fields=["status", "cancel_reason", "cancelled_at"])

        deadline = validated_data.get("deadline", instance.deadline)
        column_ids = [item["statement_column"] for item in items_data]

        columns = StatementColumn.objects.filter(
            id__in=column_ids,
            is_user_input=True
        ).select_related("statement")

        columns_map = {str(c.id): c for c in columns}

        # columns_map = {
        #     str(c.id): c
        #     for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        # }

        organization_name = instance.organization.name

        with transaction.atomic():
            # Mavjud item'lar va inner'lar — ikkita so'rov (ilgari har ustun
            # uchun get_or_create + inners + har inner uchun save/create edi).
            wanted = [columns_map[str(i["statement_column"])] for i in items_data
                      if columns_map.get(str(i["statement_column"]))]
            existing_items = {
                it.statement_column_id: it
                for it in ReportItem.objects.filter(report=instance, statement_column__in=wanted)
            }
            missing = [
                ReportItem(report=instance, statement_column=col)
                for col in wanted if col.id not in existing_items
            ]
            if missing:
                for it in ReportItem.objects.bulk_create(missing):
                    existing_items[it.statement_column_id] = it

            inners_by_item = {}
            for inner in ReportItemInner.objects.filter(report_item__in=existing_items.values()):
                inners_by_item.setdefault(inner.report_item_id, {})[str(inner.id)] = inner

            to_update, to_create, to_delete = [], [], []
            seen_columns = set()
            for item in items_data:
                column = columns_map.get(str(item["statement_column"]))
                if not column or column.id in seen_columns:
                    continue
                seen_columns.add(column.id)
                report_item = existing_items[column.id]
                existing_inners = inners_by_item.get(report_item.id, {})
                received_inner_ids = set()

                for inner_data in item.get("inners", []):
                    inner_id = str(inner_data.get("id", ""))
                    value = inner_data["value"]
                    if column.title_uz.strip().lower() == "tashkilot nomi":
                        value = organization_name

                    if inner_id and inner_id in existing_inners:
                        inner_obj = existing_inners[inner_id]
                        inner_obj.value = value
                        to_update.append(inner_obj)
                        received_inner_ids.add(inner_id)
                    else:
                        to_create.append(ReportItemInner(report_item=report_item, value=value))

                to_delete.extend(set(existing_inners) - received_inner_ids)

            if to_update:
                ReportItemInner.objects.bulk_update(to_update, ["value"])
            if to_create:
                ReportItemInner.objects.bulk_create(to_create)
            if to_delete:
                ReportItemInner.objects.filter(id__in=to_delete).delete()

            # 4. Eski hisoblangan ustunlarni o‘chirish (CALCULATED_COLUMNS asosida)
            statement_name = instance.statement.name_uz
            calculated_orderings = CALCULATED_COLUMNS.get(statement_name, [])
            if calculated_orderings:
                StatementColumn_qs = StatementColumn.objects.filter(
                    statement=instance.statement,
                    ordering__in=calculated_orderings
                )
                ReportItem.objects.filter(
                    report=instance,
                    statement_column__in=StatementColumn_qs
                ).delete()

            # 5. Hisoblash funksiyasini chaqirish
            calculate_func = ALL_CALCULATORS.get(statement_name)
            if calculate_func:
                calculate_func(instance)

            # 6. Individual, viloyat, respublika jami
            aggregate_individual_report(instance)

        return instance


class ReportDetailSerializer(CustomModelSerializer):
    report_items = serializers.SerializerMethodField()
    submit_at = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "deadline", "submit_at", "report_items"]

    def get_submit_at(self, obj):
        if obj.deadline and obj.deadline.submit_at:
            return obj.deadline.submit_at
        return None

    def _parse_bool(self, value):
        if value is None:
            return None
        value = str(value).strip().lower()
        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
        return None

    def get_report_items(self, obj):
        request = self.context.get("request")

        raw = request.query_params.get("is_user_input") if request else None
        is_user_input = self._parse_bool(raw)

        qs = (
            obj.report_items.model.objects
            .filter(report=obj)
            .select_related("statement_column")
            .prefetch_related("inners")
        )

        if is_user_input is True:
            qs = qs.filter(statement_column__is_user_input=True)
        elif is_user_input is False:
            qs = qs.filter(statement_column__is_user_input=False)
        else:
            # default — faqat user input
            qs = qs.filter(statement_column__is_user_input=True)

        # Build map once: report_item_id -> is_organization to avoid FK access inside inner serializer
        items_list = list(qs)
        is_org_by_item_id = {str(it.id): bool(getattr(it.statement_column, "is_organization", False)) for it in items_list}
        ctx = dict(self.context)
        ctx["is_org_by_item_id"] = is_org_by_item_id
        return ReportItemUpdateSerializer(items_list, many=True, context=ctx).data

