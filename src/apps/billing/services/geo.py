"""
GIS ro'yxati uchun ixcham GeoJSON: xaritaga faqat geometriya kerak —
`properties` (KMZ tavsiflari, yuzlab belgi) olib tashlanadi, koordinatalar
6 xonagacha (≈10 sm) yaxlitlanadi. 1700+ chegara bilan javob ~2 barobar kichik.
"""


def _round_coords(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, 6)
    if isinstance(value, list):
        return [_round_coords(v) for v in value]
    return value


def slim_geojson(data):
    if not isinstance(data, dict):
        return data
    kind = data.get("type")
    if kind == "FeatureCollection":
        return {"type": "FeatureCollection",
                "features": [slim_geojson(f) for f in data.get("features") or [] if isinstance(f, dict)]}
    if kind == "Feature":
        geometry = data.get("geometry")
        return {"type": "Feature", "geometry": slim_geojson(geometry) if isinstance(geometry, dict) else None}
    if "coordinates" in data:
        return {"type": kind, "coordinates": _round_coords(data.get("coordinates"))}
    return data


# ---------------------------------------------------------------------------
# Xo'jalik hududining ixcham tashqi chegarasi (landing xaritasi uchun)
# ---------------------------------------------------------------------------
OUTLINES_CACHE_KEY = "billing:public:xojalik_outlines"
OUTLINE_BUFFER = 0.003     # ~300 m: yonma-yon parcellar bitta hududga qo'shiladi
OUTLINE_TOLERANCE = 0.003  # soddalashtirish (~300 m) — respublika/viloyat ko'lamida yetarli


def _polygons(geometry: dict) -> list:
    """GeoJSON Polygon/MultiPolygon -> shapely poligonlar; buzuq halqalar tashlanadi."""
    from shapely.geometry import Polygon
    from shapely.validation import make_valid

    kind = geometry.get("type")
    if kind == "Polygon":
        parts = [geometry.get("coordinates") or []]
    elif kind == "MultiPolygon":
        parts = geometry.get("coordinates") or []
    else:
        return []
    polygons = []
    for rings in parts:
        rings = [ring for ring in rings or [] if isinstance(ring, list) and len(ring) >= 4]
        if not rings:
            continue
        try:
            polygons.append(make_valid(Polygon(rings[0], rings[1:])))
        except (ValueError, TypeError):
            continue
    return polygons


def build_outline(boundary_geojson):
    """
    Minglab mayda kontur (MultiPolygon) -> bitta soddalashtirilgan hudud chegarasi.
    72 xo'jalik: ~12.5 MB -> ~200 KB. Hisoblash og'ir (~0.2 s/xo'jalik) — import'da
    yoki `build_xojalik_outlines` buyrug'ida bir marta, so'rovda emas.
    """
    from shapely.geometry import mapping
    from shapely.ops import unary_union

    if not isinstance(boundary_geojson, dict):
        return None
    if boundary_geojson.get("type") == "FeatureCollection":
        geometries = [f.get("geometry") for f in boundary_geojson.get("features") or [] if isinstance(f, dict)]
    elif boundary_geojson.get("type") == "Feature":
        geometries = [boundary_geojson.get("geometry")]
    else:
        geometries = [boundary_geojson]
    polygons = [p for g in geometries if isinstance(g, dict) for p in _polygons(g)]
    if not polygons:
        return None
    merged = unary_union([p.buffer(OUTLINE_BUFFER) for p in polygons]).buffer(-OUTLINE_BUFFER * 0.8)
    outline = merged.simplify(OUTLINE_TOLERANCE, preserve_topology=True)
    if outline.is_empty:
        return None
    data = mapping(outline)
    return {"type": data["type"], "coordinates": _round_to(data["coordinates"], 4)}


def _round_to(value, digits):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, (list, tuple)):
        return [_round_to(v, digits) for v in value]
    return value
