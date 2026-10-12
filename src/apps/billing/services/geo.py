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
