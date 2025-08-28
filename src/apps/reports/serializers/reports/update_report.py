import uuid
from uuid import UUID
from rest_framework import serializers
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.base.serializers import CustomModelSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plan
from apps.reports.services.general_report import aggregate_general_report


# 1. INNER qiymatlari uchun serializer
class ReportItemInnerSerializer(serializers.Serializer):
    value = serializers.CharField()


# 2. ReportItem uchun serializer
class ReportItemSerializer(serializers.Serializer):
    # Kirish uchun UUIDField
    statement_column = serializers.UUIDField(write_only=True)

    # Chiqishda title ko‘rsatiladi
    statement_column_title = serializers.CharField(
        read_only=True,
        source="statement_column.title"
    )

    inners = ReportItemInnerSerializer(many=True)

    def validate_statement_column(self, value):
        if not isinstance(value, UUID):
            raise CustomExceptionError(detail=_("StatementColumn must be UUID"))
        return str(value)


# 3. Asosiy UPDATE serializer
class ReportUpdateSerializer(CustomModelSerializer):
    report_items = ReportItemSerializer(many=True)

    class Meta:
        model = Report
        fields = ["id", "deadline", "report_items"]

    def validate(self, attrs):
        items = attrs.get("report_items", [])
        deadline = attrs.get("deadline")

        if not items:
            raise serializers.ValidationError({"detail": "report_items required"})

        try:
            column_ids = [item["statement_column"] for item in items]
        except KeyError:
            raise serializers.ValidationError({
                "detail": "Each report_item must include `statement_column`."
            })

        columns_map = {
            str(c.id): c
            for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
        }

        plan_columns = []
        organization_ids = set()

        for item in items:
            col_id = str(item["statement_column"])
            column = columns_map.get(col_id)
            if not column:
                raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})

            inners = item.get("inners", [])
            if not isinstance(inners, list) or not inners:
                raise serializers.ValidationError({"detail": f"Empty or invalid inners for column {col_id}"})

            for inner in inners:
                val = inner.get("value")
                if column.is_organization:
                    organization_ids.add(val)
                elif column.status_plan:
                    try:
                        int(val)
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            "detail": f"Plan value must be integer at column {col_id}"
                        })
                    plan_columns.append(col_id)
                else:
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            "detail": f"Invalid number at column {col_id} inner"
                        })

        if len(organization_ids) != 1:
            raise serializers.ValidationError({"detail": "Multiple or missing organizations found."})

        self.validated_columns_map = columns_map
        self.validated_org_id = list(organization_ids)[0]
        self.validated_plan_values = {
            str(item["statement_column"]): item["inners"][0]["value"]
            for item in items if columns_map[str(item["statement_column"])].status_plan
        }

        if plan_columns:
            plans = Plan.objects.filter(
                column_id__in=plan_columns,
                deadline=deadline
            )
            plans_map = {str(p.column_id): p for p in plans}
            for col_id in plan_columns:
                if col_id not in plans_map or str(plans_map[col_id].plan_value) != str(
                        self.validated_plan_values[col_id]):
                    raise serializers.ValidationError({
                        "detail": f"Plan value mismatch for column {col_id}"
                    })

        return attrs

    def update(self, instance, validated_data):
        import uuid
        from django.db import transaction

        items_data = validated_data.get("report_items", [])
        deadline = validated_data.get("deadline", instance.deadline)
        org_id = self.validated_org_id
        columns_map = self.validated_columns_map
        statement = instance.statement

        with transaction.atomic():
            ReportItemInner.objects.filter(report_item__report=instance).delete()
            ReportItem.objects.filter(report=instance).delete()

            report_items = []
            report_inners = []

            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map[col_id]
                inners = item.get("inners", [])

                report_item_id = uuid.uuid4()
                report_items.append(ReportItem(
                    id=report_item_id,
                    report=instance,
                    statement_column=column
                ))

                for inner in inners:
                    report_inners.append(ReportItemInner(
                        report_item_id=report_item_id,
                        value=inner["value"]
                    ))

            ReportItem.objects.bulk_create(report_items, batch_size=1000)
            ReportItemInner.objects.bulk_create(report_inners, batch_size=2000)

            instance.deadline = deadline
            instance.save()

            aggregate_general_report(statement, deadline)

        return instance


# 4. Detail ko‘rish uchun serializer
class ReportDetailSerializer(CustomModelSerializer):
    report_items = ReportItemSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "deadline", "report_items"
        ]
