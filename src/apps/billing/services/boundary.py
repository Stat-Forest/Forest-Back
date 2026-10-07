"""
Shartnoma yer chegarasi (GeoJSON) tekshiruvi — shapely bilan (PostGIS yo'q):
faqat Polygon/MultiPolygon, invalid geometriyalar buffer(0) bilan tuzatiladi,
xo'jalik hududi bilan kesishishi shart (hudud mavjud bo'lsa), boshqa FAOL
shartnomalar bilan ustma-ust tushmasligi kerak.
"""
from shapely.geometry import shape

from apps.billing.models import Contract, Xojalik, XojalikLocation


def geojson_to_shapely(geojson_data) -> list:
    """GeoJSON (Feature/FeatureCollection/Geometry) -> shapely poligonlar ro'yxati."""
    geometries = []
    if not isinstance(geojson_data, dict):
        return geometries
    geo_type = geojson_data.get("type")
    if geo_type == "FeatureCollection":
        features = geojson_data.get("features") or []
    elif geo_type == "Feature":
        features = [geojson_data]
    else:
        features = [{"type": "Feature", "geometry": geojson_data}]

    for feature in features:
        geometry = (feature or {}).get("geometry") or feature
        if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        try:
            geometries.append(shape(geometry))
        except (ValueError, TypeError, AttributeError):
            continue
    return geometries


def _repaired(geometries: list) -> list:
    return [g if g.is_valid else g.buffer(0) for g in geometries]


def validate_contract_boundary(contract: Contract | None, xojalik: Xojalik | None, boundary_geojson) -> str | None:
    """Xato bo'lsa o'zbekcha matn, hammasi joyida bo'lsa None."""
    new_geometries = geojson_to_shapely(boundary_geojson)
    if not new_geometries:
        if boundary_geojson:
            return "Chegara faqat Polygon yoki MultiPolygon bo'lishi kerak"
        return None
    new_geometries = _repaired(new_geometries)

    if xojalik is not None:
        location = XojalikLocation.objects.filter(xojalik=xojalik, boundary_geojson__isnull=False).first()
        if location:
            xojalik_geometries = _repaired(geojson_to_shapely(location.boundary_geojson))
            if xojalik_geometries and not any(
                new_geom.intersects(xojalik_geom)
                for new_geom in new_geometries
                for xojalik_geom in xojalik_geometries
            ):
                return (
                    f"Chizilgan chegara '{location.name}' xo'jaligining o'rmon fondi yeriga to'g'ri kelmayapti "
                    f"(boshqa xo'jalik hududi yoki o'rmon fondidan tashqari joy). "
                    f"Iltimos chegarani xo'jalik hududi ichida qaytadan belgilang"
                )

    others = Contract.objects.filter(boundary_geojson__isnull=False, status=Contract.Status.ACTIVE)
    if contract is not None and contract.pk:
        others = others.exclude(id=contract.pk)

    for other in others.only("id", "number", "contract_number", "boundary_geojson"):
        other_geometries = _repaired(geojson_to_shapely(other.boundary_geojson))
        if not other_geometries:
            continue
        other_label = other.contract_number or other.number or f"#{other.id}"
        for new_geom in new_geometries:
            for other_geom in other_geometries:
                if new_geom.equals(other_geom):
                    return f"Bu chegara allaqachon {other_label} - raqamli shartnomada qayd etilgan"
                if new_geom.intersects(other_geom) and new_geom.intersection(other_geom).area > 0:
                    return (
                        f"Chizilgan chegara {other_label} - raqamli shartnoma yeriga kirib ketmoqda. "
                        f"Iltimos chegarani tekshirib qaytadan belgilang"
                    )
    return None
