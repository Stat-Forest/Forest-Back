"""Buyurtma, hujjat, xabarnoma serializer'lari (API shartnomasi TZ §21). Sanalar ISO."""
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from urllib.parse import quote

from apps.general.protected_media import is_protected, make_token
from apps.yashil.models import (
    STATE_LABELS_CYR,
    CatalogItem,
    Document,
    DocumentVersion,
    Order,
    OrderAttachment,
    OrderEvent,
    OrderLine,
    OrderVersion,
    ReturnReason,
    Signature,
    YashilNotification,
)
from apps.yashil.serializers import CatalogItemSerializer
from apps.yashil.services.units import UNIT_LABELS

ISO = serializers.DateField(format="iso-8601", read_only=True)


def _dec(value):
    if value is None:
        return None
    return format(Decimal(value).normalize(), "f")


class LineInSerializer(serializers.Serializer):
    catalog_item = serializers.PrimaryKeyRelatedField(queryset=CatalogItem.objects.all())
    qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    attrs_note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class OrderWriteSerializer(serializers.ModelSerializer):
    """Qoralama yaratish/tahrirlash. `lines` berilsa to'liq almashtiriladi."""

    lines = LineInSerializer(many=True, required=False)
    version_no = serializers.IntegerField(required=False)

    class Meta:
        model = Order
        fields = (
            "route", "supplier_org", "title", "object_type", "object_note", "season", "address", "lat", "lon",
            "polygon", "area_ha", "area_calc_ha", "area_note", "water_source", "contact_person", "extra_info",
            "base_seedlings", "problem_note", "linked_order", "repeat_reason", "lines", "version_no",
        )
        extra_kwargs = {f: {"required": False} for f in fields if f not in ("route", "supplier_org")}


class LineOutSerializer(serializers.ModelSerializer):
    catalog_item = CatalogItemSerializer(read_only=True)
    qty = serializers.SerializerMethodField()
    unit_cyr = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = ("id", "catalog_item", "qty", "unit_cyr", "attrs_note", "position")

    def get_qty(self, obj):
        return _dec(obj.qty)

    def get_unit_cyr(self, obj):
        return UNIT_LABELS.get(obj.catalog_item.unit, (obj.catalog_item.unit,))[0]


class SignatureSerializer(serializers.ModelSerializer):
    signed_at = serializers.DateTimeField(format="iso-8601")

    class Meta:
        model = Signature
        fields = ("id", "role", "signer_cn", "signer_tin", "signed_at", "mode", "is_valid", "cert_serial", "cert_valid_to")


class DocumentVersionSerializer(serializers.ModelSerializer):
    signatures = SignatureSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = ("id", "version_no", "template_version", "status", "content", "content_hash", "qr_token", "created_at", "signatures")


class DocumentVersionShortSerializer(serializers.ModelSerializer):
    signatures = SignatureSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentVersion
        fields = ("id", "version_no", "status", "qr_token", "signatures")


class DocumentSerializer(serializers.ModelSerializer):
    current_version = DocumentVersionShortSerializer(read_only=True)
    versions = DocumentVersionShortSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ("id", "kind", "number", "current_version", "versions")


class OrderVersionSerializer(serializers.ModelSerializer):
    submitted_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    superseded_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    document_version_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = OrderVersion
        fields = ("id", "version_no", "submitted_at", "superseded_at", "document_version_id")


class OrderEventSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderEvent
        fields = ("id", "action", "from_state", "to_state", "actor_name", "actor_label", "comment", "reason_code", "payload", "created_at")

    def get_actor_name(self, obj):
        u = obj.actor_user
        return f"{u.last_name} {u.first_name}".strip() if u else ""


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = OrderAttachment
        fields = ("id", "version_no", "original_name", "size", "kind", "url", "created_at")

    def get_url(self, obj):
        """Nisbiy URL (frontend o'z origin'iga qo'shadi); himoyalangan papka uchun imzoli `?t=`."""
        if not obj.file or not obj.file.name:
            return None
        url = obj.file.url
        if is_protected(obj.file.name):
            url = f"{url}?t={quote(make_token(obj.file.name))}"
        return url


class OrderListSerializer(serializers.ModelSerializer):
    mahalla_name = serializers.CharField(source="mahalla.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier_org.name", read_only=True)
    state_cyr = serializers.SerializerMethodField()
    deadline = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    last_submitted_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    delivery_due = ISO
    area_ha = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "number", "display_number", "title", "route", "state", "state_cyr", "version_no", "mahalla_name",
            "supplier_name", "area_ha", "created_at", "last_submitted_at", "delivery_due", "deadline",
        )

    def get_state_cyr(self, obj):
        return STATE_LABELS_CYR.get(obj.state, obj.state)

    def get_deadline(self, obj):
        from apps.yashil.services.transitions import deadline_info

        return deadline_info(obj)

    def get_area_ha(self, obj):
        return _dec(obj.area_ha)


class OrderDetailSerializer(OrderListSerializer):
    lines = LineOutSerializer(many=True, read_only=True)
    versions = OrderVersionSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    mahalla = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    union_unit = serializers.SerializerMethodField()
    object_type = serializers.SerializerMethodField()
    season = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    last_return = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lon = serializers.SerializerMethodField()
    area_calc_ha = serializers.SerializerMethodField()
    accepted_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    first_submitted_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + (
            "mahalla", "supplier", "union_unit", "object_type", "object_note", "season", "address", "lat", "lon",
            "polygon", "area_calc_ha", "area_note", "water_source", "contact_person", "extra_info", "base_seedlings",
            "problem_note", "linked_order", "repeat_reason", "first_submitted_at", "accepted_at", "executor_name",
            "lines", "versions", "documents", "events", "attachments", "actions", "last_return",
        )

    def get_mahalla(self, o):
        m = o.mahalla
        return {"id": str(m.id), "name": m.name, "district": m.district.name, "region": m.region.name, "source_code": m.source_code}

    def get_supplier(self, o):
        p = getattr(o.supplier_org, "supplier_profile", None)
        return {"id": str(o.supplier_org_id), "name": p.display_name if p else o.supplier_org.name, "supplier_type": p.supplier_type if p else o.route}

    def get_union_unit(self, o):
        return {"id": str(o.union_unit_id), "name": o.union_unit.name} if o.union_unit_id else None

    def get_object_type(self, o):
        t = o.object_type
        return {"id": str(t.id), "code": t.code, "name_cyr": t.name_cyr, "name_lat": t.name_lat} if t else None

    def get_season(self, o):
        s = o.season
        return {"id": str(s.id), "year": s.year, "kind": s.kind, "label_cyr": s.label_cyr} if s else None

    def get_actions(self, o):
        from apps.yashil.services.transitions import allowed_actions

        return allowed_actions(o, self.context.get("cabinet"))

    def get_last_return(self, o):
        ev = next((e for e in reversed(list(o.events.all())) if e.action == "return"), None)
        if not ev:
            return None
        return {"comment": ev.comment, "reason_code": ev.reason_code, "by": ev.payload.get("by"),
                "fields": ev.payload.get("fields", []), "at": ev.created_at.isoformat(timespec="seconds"), "actor": ev.actor_label}

    def get_lat(self, o):
        return _dec(o.lat)

    def get_lon(self, o):
        return _dec(o.lon)

    def get_area_calc_ha(self, o):
        return _dec(o.area_calc_ha)


class ReturnSerializer(serializers.Serializer):
    reason_code = serializers.ChoiceField(choices=ReturnReason.choices, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    fields = serializers.ListField(child=serializers.CharField(max_length=60), required=False)
    version_no = serializers.IntegerField(required=False)


class AcceptSerializer(serializers.Serializer):
    executor_name = serializers.CharField(required=False, allow_blank=True, max_length=300)
    version_no = serializers.IntegerField(required=False)


class SubmitSerializer(serializers.Serializer):
    document_version_id = serializers.UUIDField()
    nonce = serializers.CharField(max_length=64)
    pkcs7 = serializers.CharField()
    version_no = serializers.IntegerField(required=False)


class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    read_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    order_number = serializers.SerializerMethodField()

    class Meta:
        model = YashilNotification
        fields = ("id", "kind", "title", "body", "order", "order_number", "read_at", "created_at")

    def get_order_number(self, obj):
        return obj.order.display_number if obj.order_id else None


def parse_decimal(value, field):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        from apps.yashil.api import invalid_format

        raise invalid_format("Сон нотўғри", field)
