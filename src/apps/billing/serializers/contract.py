import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.billing.models import (
    Contract,
    ContractAction,
    ContractActionProduct,
    ContractActivity,
    ContractFile,
    ContractHistory,
    ContractLand,
    ContractPrivilege,
    ContractYearlyAmount,
)
from apps.general.protected_media import signed_file_url

from apps.billing.scope import can_view_renter_pii

from .reference import RenterFullSerializer, RenterShortSerializer, _mask


class ContractYearlyAmountSerializer(serializers.ModelSerializer):
    debt_amount = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)

    class Meta:
        model = ContractYearlyAmount
        fields = ["id", "year", "contract_amount", "calculated_amount", "paid_amount", "penalty_amount", "debt_amount"]


class ContractLandSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source="type.name", read_only=True)
    parent_type = serializers.UUIDField(source="type.parent_id", read_only=True, default=None)
    parent_type_name = serializers.CharField(source="type.parent.name", read_only=True, default=None)

    class Meta:
        model = ContractLand
        fields = ["id", "type", "type_name", "parent_type", "parent_type_name", "area"]


class ContractActivitySerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source="type.name", read_only=True)

    class Meta:
        model = ContractActivity
        fields = ["id", "type", "type_name", "area"]


class ContractPrivilegeSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source="type.name", read_only=True)

    class Meta:
        model = ContractPrivilege
        fields = ["id", "type", "type_name", "area"]


class ContractActionProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractActionProduct
        fields = ["id", "product_export", "product_amount", "export_amount"]


class ContractActionSerializer(serializers.ModelSerializer):
    products = ContractActionProductSerializer(many=True, read_only=True)

    class Meta:
        model = ContractAction
        fields = ["id", "vacancy", "own_investment", "products"]


class ContractFileSerializer(serializers.ModelSerializer):
    """Fayl ro'yxati/yuklash: xom /media/ yo'li chiqmaydi — faqat imzolangan `file_url`."""

    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContractFile
        fields = ["id", "contract", "file", "file_name", "file_url", "description", "uploaded_by_name", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_name(self, obj) -> str:
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""

    def get_file_url(self, obj) -> str | None:
        return signed_file_url(self.context.get("request"), obj.file)

    def get_uploaded_by_name(self, obj) -> str | None:
        user = obj.uploaded_by
        if not user:
            return None
        return f"{user.first_name} {user.last_name}".strip() or user.email


class ContractFileEmbeddedSerializer(ContractFileSerializer):
    class Meta(ContractFileSerializer.Meta):
        fields = ["id", "file_name", "file_url", "description", "uploaded_by_name", "created_at"]


_RENTER_LABEL = re.compile(r"^(?P<name>.*) \((?P<ident>\d{9,14})\)$")


def _mask_history_data(value):
    """PII rolisiz foydalanuvchi uchun: eski billing tarixi (`legacy` — ijarachi
    JSHSHIR/pasport/manzil/telefon) olib tashlanadi, "F.I.Sh. (JSHSHIR)" maskalanadi."""
    if isinstance(value, dict):
        return {key: _mask_history_data(item) for key, item in value.items() if key != "legacy"}
    if isinstance(value, list):
        return [_mask_history_data(item) for item in value]
    if isinstance(value, str):
        match = _RENTER_LABEL.match(value)
        if match:
            return f'{match["name"]} ({_mask(match["ident"])})'
    return value


class ContractHistorySerializer(serializers.ModelSerializer):
    executor_name = serializers.SerializerMethodField()

    class Meta:
        model = ContractHistory
        fields = ["id", "reason", "data", "executor_name", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is None or not can_view_renter_pii(request.user):
            data["data"] = _mask_history_data(data["data"])
        return data

    def get_executor_name(self, obj) -> str | None:
        user = obj.executor
        if not user:
            return None
        return f"{user.first_name} {user.last_name}".strip() or user.email


class ContractListSerializer(serializers.ModelSerializer):
    xojalik_name = serializers.CharField(source="xojalik.name", read_only=True)
    xojalik_inn = serializers.CharField(source="xojalik.inn", read_only=True)
    bolim_name = serializers.CharField(source="bolim.name", read_only=True, default=None)
    region_name = serializers.CharField(source="region.name", read_only=True, default=None)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    renter = RenterShortSerializer(read_only=True)
    debt = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    has_boundary = serializers.BooleanField(read_only=True)
    files_count = serializers.SerializerMethodField()
    days_remaining = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "number", "contract_number", "status", "contract_date", "expired_date", "canceled_date",
            "cancel_reason", "xojalik", "xojalik_name", "xojalik_inn", "bolim", "bolim_name", "region",
            "region_name", "district", "district_name", "renter", "rent_area", "rent_amount", "paid_amount",
            "penalty_amount", "debt", "latitude", "longitude", "has_boundary", "files_count", "days_remaining",
            "is_expired", "created_at",
        ]

    def get_files_count(self, obj) -> int:
        count = getattr(obj, "files_count", None)
        return count if count is not None else obj.files.count()


class ContractDetailSerializer(ContractListSerializer):
    renter = RenterFullSerializer(read_only=True)
    yearly_amounts = ContractYearlyAmountSerializer(many=True, read_only=True)
    lands = ContractLandSerializer(many=True, read_only=True)
    activities = ContractActivitySerializer(many=True, read_only=True)
    privileges = ContractPrivilegeSerializer(many=True, read_only=True)
    action = serializers.SerializerMethodField()
    files = ContractFileEmbeddedSerializer(many=True, read_only=True)

    class Meta(ContractListSerializer.Meta):
        fields = ContractListSerializer.Meta.fields + [
            "boundary_geojson", "cadastral_number", "circle", "section", "counter", "massive",
            "auction_date", "exemptioned_date", "is_entity", "yearly_amounts", "lands", "activities",
            "privileges", "action", "files",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is None or not can_view_renter_pii(request.user):
            # Shartnoma skanlari (pasport nusxalari va h.k.) — /contract-files/ kabi
            # faqat PII rollariga (audit A4); imzolangan havolalar berilmaydi.
            data["files"] = []
        return data

    @extend_schema_field(ContractActionSerializer(allow_null=True))
    def get_action(self, obj):
        action = next(iter(obj.actions.all()), None)
        return ContractActionSerializer(action).data if action else None


class ContractSummarySerializer(serializers.Serializer):
    total_count = serializers.IntegerField()
    total_rent_area = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_rent_amount = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_paid_amount = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_penalty_amount = serializers.DecimalField(max_digits=22, decimal_places=2)
    total_debt = serializers.DecimalField(max_digits=22, decimal_places=2)
