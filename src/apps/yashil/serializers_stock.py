"""Ombor API serializer'lari (TZ §9): kirim/boshlang'ich qoldiq kiritish, harakat ko'rinishi. Sanalar ISO."""
from decimal import Decimal
from urllib.parse import quote

from rest_framework import serializers

from apps.general.protected_media import is_protected, make_token
from apps.yashil.models import CatalogItem, StockMovement
from apps.yashil.services import lang


def _dec(value):
    return format(Decimal(value).normalize(), "f") if value is not None else None


def relative_signed_url(file_field):
    if not file_field or not getattr(file_field, "name", None):
        return None
    url = file_field.url
    if is_protected(file_field.name):
        url = f"{url}?t={quote(make_token(file_field.name))}"
    return url


class StockEntrySerializer(serializers.Serializer):
    """Kirim / boshlang'ich qoldiq / haqiqiy qaytarish kiritish."""

    catalog_item = serializers.PrimaryKeyRelatedField(queryset=CatalogItem.objects.all())
    qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    doc_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    doc_date = serializers.DateField(input_formats=["iso-8601"], required=False, allow_null=True, default=None)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ReversalRequestSerializer(serializers.Serializer):
    movement = serializers.UUIDField()
    note = serializers.CharField(max_length=1000)


class DecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class StockMovementSerializer(serializers.ModelSerializer):
    qty = serializers.SerializerMethodField()
    catalog_item = serializers.SerializerMethodField()
    doc_date = serializers.DateField(format="iso-8601", read_only=True)
    file_url = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    requested_by = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    approved_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    reversal_of = serializers.UUIDField(source="reversal_of_id", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id", "kind", "status", "qty", "catalog_item", "doc_number", "doc_date", "note", "file_url", "order_number",
            "reversal_of", "requested_by", "approved_by_name", "approved_at", "decision_note", "created_at",
        )

    def get_qty(self, obj) -> str | None:
        return _dec(obj.qty)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if obj.kind in (StockMovement.Kind.ALLOCATE, StockMovement.Kind.RELEASE):
            data["note"] = lang.tr_known(data["note"])  # tizim izohi («Буюртма …»)
        return data

    def get_catalog_item(self, obj) -> dict | None:
        i = obj.catalog_item
        return {"id": str(i.id), "code": i.code, "name_cyr": i.name_cyr, "name_lat": i.name_lat, "unit": i.unit}

    def get_file_url(self, obj) -> str | None:
        return relative_signed_url(obj.file)

    def get_order_number(self, obj) -> str | None:
        if obj.order_line_id:
            return obj.order_line.order.number
        if obj.acceptance_id:
            return obj.acceptance.order.number
        return None

    def get_requested_by(self, obj) -> str:
        m = obj.requested_by_membership
        return f"{m.user.last_name} {m.user.first_name}".strip() if m else ""

    def get_approved_by_name(self, obj) -> str | None:
        u = obj.approved_by
        return f"{u.last_name} {u.first_name}".strip() if u else ""
