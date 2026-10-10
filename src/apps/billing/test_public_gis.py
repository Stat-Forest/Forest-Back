"""Ochiq (login'siz) GIS xarita endpointlari — landing sahifa uchun."""
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user
from apps.billing.models import Contract
from apps.billing.test_gis import make_location

PUBLIC = f"{BASE}/public"


class PublicGisTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.location = make_location(self.ref)
        writer = auth(self.client_class(), make_user("super", "billing_super"))
        self.active = writer.post(f"{BASE}/contracts/", contract_payload(self.ref, contract_number="PUB-1"), format="json").data
        self.inactive = writer.post(
            f"{BASE}/contracts/", contract_payload(self.ref, contract_number="PUB-2", pinfl="22222222222222"), format="json",
        ).data
        Contract.objects.filter(pk=self.inactive["id"]).update(status=Contract.Status.INACTIVE)
        no_location = contract_payload(self.ref, contract_number="PUB-3", pinfl="33333333333333", latitude=None, longitude=None)
        writer.post(f"{BASE}/contracts/", no_location, format="json")
        cache.clear()

    def test_geo_list_is_anonymous_active_only_and_without_private_data(self):
        resp = self.client.get(f"{PUBLIC}/geo-list/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["total_area"], 12.5)
        row = resp.data["results"][0]
        self.assertEqual(row["contract_number"], "PUB-1")
        self.assertEqual(
            set(row),
            {"id", "number", "contract_number", "latitude", "longitude", "boundary_geojson", "rent_area",
             "xojalik_name", "activity_name"},
        )
        self.assertIsInstance(row["latitude"], float)

    def test_geo_list_filters(self):
        self.assertEqual(self.client.get(f"{PUBLIC}/geo-list/", {"number": "pub-1"}).data["count"], 1)
        self.assertEqual(self.client.get(f"{PUBLIC}/geo-list/", {"number": "yo'q"}).data["count"], 0)
        other = make_reference(code="11:11:11", inn="987654321", name="Boshqa DÒX")
        self.assertEqual(self.client.get(f"{PUBLIC}/geo-list/", {"xojalik": str(other.xojalik.id)}).data["count"], 0)
        self.assertEqual(self.client.get(f"{PUBLIC}/geo-list/", {"xojalik": "bad"}).status_code, 400)

    def test_locations_and_konturs_are_anonymous(self):
        listed = self.client.get(f"{PUBLIC}/xojalik-locations/")
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn("boundary_geojson", listed.data[0])
        detail = self.client.get(f"{PUBLIC}/xojalik-locations/{self.location.id}/")
        self.assertEqual(detail.data["boundary_geojson"]["type"], "Feature")

        self.assertEqual(self.client.get(f"{PUBLIC}/xojalik-konturs/").data, [])  # parametrsiz — bo'sh
        konturs = self.client.get(f"{PUBLIC}/xojalik-konturs/", {"xojalik_location": str(self.location.id)}).data
        self.assertEqual(len(konturs), 1)
        kontur = self.client.get(f"{PUBLIC}/xojalik-konturs/{konturs[0]['id']}/").data
        self.assertEqual(kontur["xojalik_name"], self.ref.xojalik.name)

    def test_public_endpoints_are_read_only(self):
        self.assertEqual(self.client.post(f"{PUBLIC}/xojalik-locations/", {}).status_code, 405)
        self.assertEqual(self.client.post(f"{PUBLIC}/geo-list/", {}).status_code, 405)
