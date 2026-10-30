"""Dalolatnoma API serializer'lari (TZ §10, §12, §21). Sanalar ISO."""
from decimal import Decimal

from rest_framework import serializers

from apps.yashil.models import STATE_LABELS_CYR, Act, ActAttachment, ActLine, ActReturnReason, ActVersion
from apps.yashil.serializers_orders import DocumentSerializer
from apps.yashil.serializers_stock import relative_signed_url
from apps.yashil.services.units import UNIT_LABELS

ACT_STATUS_CYR = {
    Act.Status.DRAFT: "Қоралама",
    Act.Status.REVIEW: "Маҳалла тасдиғида",
    Act.Status.APPROVED: "Қабул қилинган",
    Act.Status.RETURNED: "Тузатиш учун қайтарилган",
    Act.Status.CANCELLED: "Бекор қилинган",
}


def _dec(value):
    return format(Decimal(value).normalize(), "f") if value is not None else None


class ActLineInSerializer(serializers.Serializer):
    order_line = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=18, decimal_places=4)


class ActWriteSerializer(serializers.Serializer):
    delivery_date = serializers.DateField(input_formats=["iso-8601"])
    planned_date = serializers.DateField(input_formats=["iso-8601"], required=False, allow_null=True, default=None)
    responsible = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    delivery_address = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    lines = ActLineInSerializer(many=True, required=False, default=list)


class ActReturnSerializer(serializers.Serializer):
    reason_code = serializers.ChoiceField(choices=ActReturnReason.choices, required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=False, allow_blank=True, max_length=4000, default="")


class ActCancelSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=4000, default="")


class ActSignSerializer(serializers.Serializer):
    document_version_id = serializers.UUIDField()
    nonce = serializers.CharField(max_length=64)
    pkcs7 = serializers.CharField()


class ActLineOutSerializer(serializers.ModelSerializer):
    order_line = serializers.UUIDField(source="order_line_id", read_only=True)
    catalog_item = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()
    ordered_qty = serializers.SerializerMethodField()
    unit_cyr = serializers.SerializerMethodField()

    class Meta:
        model = ActLine
        fields = ("id", "order_line", "catalog_item", "qty", "ordered_qty", "unit_cyr")

    def get_catalog_item(self, obj) -> dict | None:
        i = obj.order_line.catalog_item
        return {"id": str(i.id), "code": i.code, "name_cyr": i.name_cyr, "name_lat": i.name_lat, "unit": i.unit, "precision": i.precision}

    def get_qty(self, obj) -> str | None:
        return _dec(obj.qty)

    def get_ordered_qty(self, obj) -> str | None:
        return _dec(obj.order_line.qty)

    def get_unit_cyr(self, obj) -> str | None:
        return UNIT_LABELS.get(obj.order_line.catalog_item.unit, (obj.order_line.catalog_item.unit,))[0]


class ActVersionSerializer(serializers.ModelSerializer):
    lines = ActLineOutSerializer(many=True, read_only=True)
    delivery_date = serializers.DateField(format="iso-8601", read_only=True)
    planned_date = serializers.DateField(format="iso-8601", read_only=True)
    document_version_id = serializers.UUIDField(read_only=True)
    submitted_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    superseded_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = ActVersion
        fields = ("id", "version_no", "delivery_date", "planned_date", "responsible", "delivery_address", "note", "lines",
                  "document_version_id", "submitted_at", "superseded_at", "created_at")


class ActAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = ActAttachment
        fields = ("id", "version_no", "original_name", "size", "kind", "url", "created_at")

    def get_url(self, obj) -> str | None:
        return relative_signed_url(obj.file)


class ActListSerializer(serializers.ModelSerializer):
    status_cyr = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    delivery_date = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    approved_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    returned_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    updated_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = Act
        fields = ("id", "number", "index", "status", "status_cyr", "version_no", "is_partial", "order", "delivery_date",
                  "approved_at", "returned_at", "created_at", "updated_at", "actions")

    def get_status_cyr(self, obj) -> str | None:
        return ACT_STATUS_CYR.get(obj.status, obj.status)

    def get_order(self, obj) -> dict | None:
        o = obj.order
        return {"id": str(o.id), "number": o.number, "title": o.title, "state": o.state, "state_cyr": STATE_LABELS_CYR.get(o.state, o.state),
                "mahalla_name": o.mahalla.name, "supplier_name": o.supplier_org.name, "route": o.route}

    def get_delivery_date(self, obj) -> str | None:
        v = obj.current_version
        return v.delivery_date.isoformat() if v else None

    def get_actions(self, obj) -> list[str]:
        from apps.yashil.services.acts import allowed_act_actions

        return allowed_act_actions(obj, self.context.get("cabinet"))


class ActDetailSerializer(ActListSerializer):
    current_version = ActVersionSerializer(read_only=True)
    versions = ActVersionSerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()
    document = DocumentSerializer(read_only=True)
    last_return = serializers.SerializerMethodField()

    class Meta(ActListSerializer.Meta):
        fields = ActListSerializer.Meta.fields + ("current_version", "versions", "attachments", "document", "last_return")

    def get_attachments(self, obj) -> list[dict]:
        rows = [a for a in obj.attachments.all() if a.version_no == obj.version_no]
        return ActAttachmentSerializer(rows, many=True, context=self.context).data

    def get_last_return(self, obj) -> dict | None:
        from apps.yashil.services.acts import last_return_of

        return last_return_of(obj)
