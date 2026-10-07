from rest_framework import serializers

from apps.billing.models import XojalikKontur, XojalikLocation


class XojalikLocationSerializer(serializers.ModelSerializer):
    """Ro'yxat — boundary_geojson'siz (xaritaga barcha xo'jaliklar yengil yuklanadi)."""

    region_name = serializers.CharField(source="region.name", read_only=True)
    xojalik_name = serializers.CharField(source="xojalik.name", read_only=True, default=None)

    class Meta:
        model = XojalikLocation
        fields = [
            "id", "name", "region", "region_name", "xojalik", "xojalik_name",
            "latitude", "longitude", "bounds", "area_ga", "parcel_count",
        ]


class XojalikLocationDetailSerializer(XojalikLocationSerializer):
    class Meta(XojalikLocationSerializer.Meta):
        fields = XojalikLocationSerializer.Meta.fields + ["boundary_geojson"]


class XojalikKonturSerializer(serializers.ModelSerializer):
    class Meta:
        model = XojalikKontur
        fields = ["id", "kontur_raqami", "area_ga"]


class XojalikKonturDetailSerializer(XojalikKonturSerializer):
    xojalik_name = serializers.CharField(source="xojalik_location.name", read_only=True)
    region_name = serializers.CharField(source="xojalik_location.region.name", read_only=True)

    class Meta(XojalikKonturSerializer.Meta):
        fields = XojalikKonturSerializer.Meta.fields + [
            "xojalik_location", "xojalik_name", "region_name", "latitude", "longitude", "bounds", "attributes", "geojson",
        ]
