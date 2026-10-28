from rest_framework import serializers

from apps.billing.models import District, Region
from apps.general.models import Organization
from apps.yashil.models import (
    CalendarDay,
    CatalogItem,
    Mahalla,
    ObjectType,
    Season,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "code", "name")


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ("id", "code", "name", "region_id")


class MahallaSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = Mahalla
        fields = ("id", "source_code", "name", "region", "district", "address", "is_active")


class MahallaShortSerializer(serializers.ModelSerializer):
    district = DistrictSerializer(read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = Mahalla
        fields = ("id", "source_code", "name", "region_name", "district", "address")


class UnionUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnionUnit
        fields = ("id", "name", "level", "region_id", "district_id")


class SupplierSerializer(serializers.Serializer):
    """`SupplierProfile` -> tashkilot ko'rinishi."""

    id = serializers.UUIDField(source="organization_id")
    name = serializers.SerializerMethodField()
    supplier_type = serializers.CharField()
    region = serializers.CharField(source="organization.region")
    parent_id = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.display_name

    def get_parent_id(self, obj):
        return str(obj.parent.organization_id) if obj.parent_id else None


class CabinetSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="cabinet_name", read_only=True)
    mahalla = MahallaShortSerializer(read_only=True)
    union_unit = UnionUnitSerializer(read_only=True)
    organization = serializers.SerializerMethodField()
    supplier_type = serializers.CharField(read_only=True)

    class Meta:
        model = YashilMembership
        fields = (
            "id", "member_type", "name", "mahalla", "union_unit", "organization", "supplier_type",
            "can_prepare", "can_sign", "position_title", "phone", "observer_scope",
        )

    def get_organization(self, obj):
        if not obj.organization_id:
            return None
        org: Organization = obj.organization
        return {"id": str(org.id), "name": org.name, "region": org.region}


class CatalogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogItem
        fields = (
            "id", "code", "name_cyr", "name_lat", "supplier_type", "item_type", "category", "unit",
            "precision", "attributes", "version",
        )


class SeasonSerializer(serializers.ModelSerializer):
    label_cyr = serializers.CharField(read_only=True)
    date_from = serializers.DateField(format="iso-8601")
    date_to = serializers.DateField(format="iso-8601")

    class Meta:
        model = Season
        fields = ("id", "year", "kind", "date_from", "date_to", "label_cyr")


class ObjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectType
        fields = ("id", "code", "name_cyr", "name_lat", "requires_note")


class CalendarDaySerializer(serializers.ModelSerializer):
    # Modul API'sida sanalar ISO (YYYY-MM-DD); loyiha standarti dd.mm.yyyy faqat eski endpointlarda.
    date = serializers.DateField(format="iso-8601")

    class Meta:
        model = CalendarDay
        fields = ("id", "date", "kind", "note", "source_ref")


SUPPLIER_TYPE_LABELS = {k: v for k, v in SupplierProfile.SupplierType.choices}
