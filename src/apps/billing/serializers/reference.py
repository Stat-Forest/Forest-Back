from rest_framework import serializers

from apps.billing.scope import can_view_renter_pii

from apps.billing.models import ActivityType, Bolim, District, LandType, PrivilegeType, Region, Renter, Xojalik


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name", "code"]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "region", "name", "code"]


class XojalikSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = Xojalik
        fields = ["id", "name", "inn", "code", "region", "region_name", "is_active"]


class BolimSerializer(serializers.ModelSerializer):
    xojalik_name = serializers.CharField(source="xojalik.name", read_only=True)

    class Meta:
        model = Bolim
        fields = ["id", "name", "xojalik", "xojalik_name"]


class _TypeSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        fields = ["id", "name", "description", "parent", "parent_name"]


class LandTypeSerializer(_TypeSerializer):
    class Meta(_TypeSerializer.Meta):
        model = LandType


class ActivityTypeSerializer(_TypeSerializer):
    class Meta(_TypeSerializer.Meta):
        model = ActivityType


class PrivilegeTypeSerializer(_TypeSerializer):
    class Meta(_TypeSerializer.Meta):
        model = PrivilegeType
        fields = _TypeSerializer.Meta.fields + ["month"]


def _mask(value, keep=2):
    if not value:
        return value
    value = str(value)
    if len(value) <= keep * 2:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep * 2) + value[-keep:]


class _RenterPIIMaskMixin:
    """PII rollaridan tashqari foydalanuvchilarga PINFL/pasport maskalanadi, telefon/manzil
    berilmaydi (audit A4). Nested serializer context'i root'dan keladi."""

    MASKED = ("pinfl", "passport")
    HIDDEN = ("phone", "per_adr", "citizenship", "birth_place")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and can_view_renter_pii(request.user):
            return data
        for field in self.MASKED:
            if field in data:
                data[field] = _mask(data[field])
        for field in self.HIDDEN:
            if field in data:
                data[field] = None
        return data


class RenterShortSerializer(_RenterPIIMaskMixin, serializers.ModelSerializer):
    class Meta:
        model = Renter
        fields = ["id", "full_name", "pinfl", "stir", "phone", "passport"]


class RenterSerializer(_RenterPIIMaskMixin, serializers.ModelSerializer):
    contracts_count = serializers.SerializerMethodField()

    class Meta:
        model = Renter
        fields = [
            "id", "full_name", "pinfl", "stir", "phone", "passport", "per_adr",
            "citizenship", "birth_place", "contracts_count",
        ]

    def get_contracts_count(self, obj) -> int:
        count = getattr(obj, "contracts_count", None)
        return count if count is not None else obj.contracts.count()


class RenterFullSerializer(RenterSerializer):
    class Meta(RenterSerializer.Meta):
        fields = RenterSerializer.Meta.fields + ["is_legal_entity", "legal_name"]
