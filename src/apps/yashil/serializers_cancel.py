"""Bekor qilish so'rovi serializer'lari (TZ §9.3; javob Е4)."""
from rest_framework import serializers

from apps.yashil.models import STATE_LABELS_CYR, CancelRequest
from apps.yashil.serializers_orders import DocumentSerializer

CANCEL_STATUS_CYR = {
    CancelRequest.Status.REQUESTED: "Сўралган",
    CancelRequest.Status.AGREED: "Иккинчи тараф келишган",
    CancelRequest.Status.APPROVED: "Уюшма тасдиқлаган",
    CancelRequest.Status.REJECTED: "Рад этилган",
}


class CancelLineInSerializer(serializers.Serializer):
    order_line = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=18, decimal_places=4)


class CancelRequestWriteSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    lines = CancelLineInSerializer(many=True, required=False, default=list)


class CancelDecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")


class CancelRequestSerializer(serializers.ModelSerializer):
    status_cyr = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    requested_by = serializers.SerializerMethodField()
    agreed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    document = DocumentSerializer(read_only=True)
    created_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    agreed_at = serializers.DateTimeField(format="iso-8601", read_only=True)
    approved_at = serializers.DateTimeField(format="iso-8601", read_only=True)

    class Meta:
        model = CancelRequest
        fields = ("id", "order", "requested_by_party", "requested_by", "is_full", "lines", "reason", "status", "status_cyr",
                  "agreed_by_name", "agreed_at", "approved_by_name", "approved_at", "decision_note", "document", "result", "created_at")

    def get_status_cyr(self, obj):
        return CANCEL_STATUS_CYR.get(obj.status, obj.status)

    def get_order(self, obj):
        o = obj.order
        return {"id": str(o.id), "number": o.number, "title": o.title, "state": o.state, "state_cyr": STATE_LABELS_CYR.get(o.state, o.state),
                "mahalla_name": o.mahalla.name, "supplier_name": o.supplier_org.name}

    def get_requested_by(self, obj):
        m = obj.requested_by_membership
        return {"cabinet": m.cabinet_name, "name": f"{m.user.last_name} {m.user.first_name}".strip()}

    def get_agreed_by_name(self, obj):
        return obj.agreed_by.cabinet_name if obj.agreed_by else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.cabinet_name if obj.approved_by else None
