"""GIS ro'yxati: chegara GeoJSON'i ixcham (properties'siz, 6 xonali koordinata)."""
from django.test import SimpleTestCase

from apps.billing.services.geo import slim_geojson


class SlimGeoJsonTest(SimpleTestCase):
    def test_strips_properties_and_rounds_coordinates(self):
        feature = {
            "type": "Feature",
            "properties": {"name": "c1", "description": "x" * 500},
            "geometry": {"type": "Polygon", "coordinates": [[[66.1234567891, 40.9876543219], [66.2, 40.9], [66.1234567891, 40.9876543219]]]},
        }
        slim = slim_geojson(feature)
        # Feature shakli saqlanadi (Leaflet L.geoJSON uchun), properties yo'q, 6 xona
        self.assertEqual(slim, {"type": "Feature", "geometry": {
            "type": "Polygon", "coordinates": [[[66.123457, 40.987654], [66.2, 40.9], [66.123457, 40.987654]]]}})

    def test_feature_collection_and_multipolygon(self):
        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[1.00000001, 2], [1, 3], [1.00000001, 2]]]}},
            {"type": "Feature", "properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [[[[5, 6], [5, 7], [5, 6]]]]}},
        ]}
        slim = slim_geojson(fc)
        self.assertEqual(slim["type"], "FeatureCollection")
        self.assertEqual([f["geometry"]["type"] for f in slim["features"]], ["Polygon", "MultiPolygon"])
        self.assertNotIn("properties", slim["features"][0])
        self.assertEqual(slim["features"][0]["geometry"]["coordinates"][0][0], [1.0, 2])

    def test_non_dict_passthrough(self):
        self.assertIsNone(slim_geojson(None))
        self.assertEqual(slim_geojson({"type": "Point", "coordinates": [1.23456789, 2]}), {"type": "Point", "coordinates": [1.234568, 2]})
