"""
Yozish (create/update/import) uchun serializerlar — `ContractWritePayload`
bo'limlari. Sanalar `dd.mm.yyyy` yoki ISO.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.billing.models import (
    ActivityType,
    Bolim,
    Contract,
    ContractAction,
    ContractActionProduct,
    District,
    LandType,
    PrivilegeType,
    Renter,
)

DATE_INPUT_FORMATS = ["%d.%m.%Y", "%Y-%m-%d"]
AMOUNT_FIELDS = ("rent_amount", "paid_amount", "penalty_amount", "rent_area")
COORD_FIELDS = ("latitude", "longitude")


class BillingDateField(serializers.DateField):
    def __init__(self, **kwargs):
        kwargs.setdefault("input_formats", DATE_INPUT_FORMATS)
        super().__init__(**kwargs)


class ContractWriteSerializer(serializers.ModelSerializer):
    contract_date = BillingDateField()
    expired_date = BillingDateField(required=False, allow_null=True)
    auction_date = BillingDateField(required=False, allow_null=True)
    exemptioned_date = BillingDateField(required=False, allow_null=True)

    class Meta:
        model = Contract
        fields = [
            "contract_date", "expired_date", "contract_number", "xojalik", "bolim", "region", "district",
            "rent_amount", "paid_amount", "penalty_amount", "rent_area", "cadastral_number",
            "circle", "section", "counter", "massive", "latitude", "longitude", "boundary_geojson",
            "auction_date", "exemptioned_date",
        ]

    def to_internal_value(self, data):
        data = dict(data)
        for field in AMOUNT_FIELDS:
            if field in data and data[field] in ("", None):
                data[field] = 0
        for field in COORD_FIELDS:
            if field in data and data[field] == "":
                data[field] = None
        if data.get("contract_number") is not None:
            data["contract_number"] = str(data["contract_number"]).strip() or None
        return super().to_internal_value(data)

    def _current(self, attrs, name):
        if name in attrs:
            return attrs[name]
        return getattr(self.instance, name, None) if self.instance else None

    def validate(self, attrs):
        errors = {}
        xojalik = self._current(attrs, "xojalik")
        bolim = self._current(attrs, "bolim")
        region = self._current(attrs, "region")
        district = self._current(attrs, "district")
        contract_date = self._current(attrs, "contract_date")
        expired_date = self._current(attrs, "expired_date")

        if isinstance(bolim, Bolim) and xojalik and bolim.xojalik_id != xojalik.id:
            errors["bolim"] = "Bu xo'jalikning bunday bo'limi mavjud emas"
        if isinstance(district, District) and region and district.region_id != region.id:
            errors["district"] = "Tuman tanlangan viloyatga mos kelmaydi"
        if contract_date and expired_date and expired_date <= contract_date:
            errors["expired_date"] = "Tugash sanasi shartnoma sanasidan katta bo'lishi kerak"
        for field in ("rent_amount", "paid_amount", "penalty_amount", "rent_area"):
            if attrs.get(field) is not None and attrs[field] < 0:
                errors[field] = "Manfiy bo'lishi mumkin emas"
        # Ijara maydoni majburiy (billing-urmon'dagi kabi): yaratishda berilishi,
        # berilganda esa noldan katta bo'lishi kerak.
        rent_area = attrs.get("rent_area")
        if "rent_area" not in errors and (
            (self.instance is None and not rent_area) or ("rent_area" in attrs and rent_area is not None and rent_area <= 0)
        ):
            errors["rent_area"] = "Ijara maydoni kiritilishi shart (0 dan katta)"

        contract_number = attrs.get("contract_number")
        if contract_number:
            clash = Contract.objects.filter(contract_number=contract_number)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                errors["contract_number"] = f"{contract_number} - raqamli shartnoma tizimda allaqachon mavjud"
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class RenterWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Renter
        fields = [
            "pinfl", "stir", "full_name", "passport", "phone", "per_adr",
            "citizenship", "birth_place", "is_legal_entity", "legal_name",
        ]
        extra_kwargs = {
            "pinfl": {"required": False, "allow_null": True, "allow_blank": True},
            "stir": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def validate(self, attrs):
        for field in ("pinfl", "stir"):
            if field in attrs:
                attrs[field] = (str(attrs[field]).strip() or None) if attrs[field] is not None else None
        pinfl = attrs["pinfl"] if "pinfl" in attrs else getattr(self.instance, "pinfl", None)
        stir = attrs["stir"] if "stir" in attrs else getattr(self.instance, "stir", None)
        if not pinfl and not stir:
            raise serializers.ValidationError({"pinfl": "INN yoki JSHSHIR'dan kamida bittasi kiritilishi shart."})
        if "is_legal_entity" not in attrs and self.instance is None:
            attrs["is_legal_entity"] = bool(stir and not pinfl)
        return attrs


class _TypeItemSerializer(serializers.Serializer):
    """lands / activities / privileges elementi: {id?, type, area} (`delete` writer'da qayta ishlanadi)."""

    id = serializers.UUIDField(required=False)
    area = serializers.DecimalField(max_digits=13, decimal_places=2, min_value=Decimal("0"))

    def to_internal_value(self, data):
        data = {k: v for k, v in dict(data).items() if k != "delete"}
        if data.get("area") == "":
            data["area"] = None
        return super().to_internal_value(data)


class LandItemSerializer(_TypeItemSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=LandType.objects.all())


class ActivityItemSerializer(_TypeItemSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=ActivityType.objects.all())


class PrivilegeItemSerializer(_TypeItemSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=PrivilegeType.objects.all())


class ActionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractAction
        fields = ["vacancy", "own_investment"]

    def to_internal_value(self, data):
        data = {k: (None if v == "" else v) for k, v in dict(data).items()}
        return super().to_internal_value(data)


class ActionProductWriteSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    delete = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = ContractActionProduct
        fields = ["id", "product_export", "product_amount", "export_amount", "delete"]

    def to_internal_value(self, data):
        data = {k: (None if v == "" else v) for k, v in dict(data).items()}
        return super().to_internal_value(data)


class YearlyAmountWriteSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    contract_amount = serializers.DecimalField(max_digits=22, decimal_places=2, required=False, default=0)
    calculated_amount = serializers.DecimalField(max_digits=22, decimal_places=2, required=False, default=0)
    paid_amount = serializers.DecimalField(max_digits=22, decimal_places=2, required=False, default=0)
    penalty_amount = serializers.DecimalField(max_digits=22, decimal_places=2, required=False, default=0)

    def to_internal_value(self, data):
        data = dict(data)
        for field in ("contract_amount", "calculated_amount", "paid_amount", "penalty_amount"):
            if data.get(field) in ("", None):
                data[field] = 0
        return super().to_internal_value(data)


class ContractStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Contract.Status.choices)
    cancel_reason = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)

    def validate(self, attrs):
        if attrs["status"] == Contract.Status.INACTIVE and not (attrs.get("cancel_reason") or "").strip():
            raise serializers.ValidationError(
                {"cancel_reason": "Shartnomani 'Faol emas' holatiga o'tkazish uchun sabab ko'rsatilishi shart"}
            )
        return attrs


class ChangeRenterSerializer(serializers.Serializer):
    renter = serializers.PrimaryKeyRelatedField(queryset=Renter.objects.all())


class ImportRowsSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField(), allow_empty=False, max_length=200)
