"""GIS: xo'jalik joylashuvi/konturlar API, chegara tekshiruvi, seed/import buyruqlari."""
import gzip
import io
import json
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user, square
from apps.billing.models import (
    ActivityType,
    Bolim,
    Contract,
    District,
    LandType,
    PrivilegeType,
    Region,
    Renter,
    Xojalik,
    XojalikKontur,
    XojalikLocation,
)

URL = f"{BASE}/contracts/"


def make_location(ref, name=None, lon=72.0, lat=40.0, size=1.0, xojalik=True):
    location = XojalikLocation.objects.create(
        name=name or ref.xojalik.name, region=ref.region, xojalik=ref.xojalik if xojalik else None,
        latitude=lat + size / 2, longitude=lon + size / 2, bounds=[[lat, lon], [lat + size, lon + size]],
        boundary_geojson={"type": "Feature", "geometry": square(lon, lat, size), "properties": {}},
        area_ga=100, parcel_count=1,
    )
    XojalikKontur.objects.create(
        xojalik_location=location, seq=0, kontur_raqami="12", raqami_num=12, latitude=lat, longitude=lon,
        bounds=location.bounds, area_ga=100, attributes={"a": "1"}, geojson=square(lon, lat, size),
    )
    return location


class GisApiTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.location = make_location(self.ref)
        self.client = auth(self.client, make_user("reader", "tashkilot_hodimi"))

    def test_locations_list_and_detail(self):
        resp = self.client.get(f"{BASE}/xojalik-locations/", {"region": str(self.ref.region.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        row = resp.data[0]
        self.assertNotIn("boundary_geojson", row)
        self.assertEqual(str(row["xojalik"]), str(self.ref.xojalik.id))
        self.assertEqual(row["xojalik_name"], self.ref.xojalik.name)
        self.assertEqual(row["region_name"], "Андижон вилояти")
        detail = self.client.get(f"{BASE}/xojalik-locations/{self.location.id}/").data
        self.assertEqual(detail["boundary_geojson"]["type"], "Feature")
        self.assertEqual(self.client.get(f"{BASE}/xojalik-locations/", {"region": str(Region.objects.create(name="X", code="99").id)}).data, [])

    def test_konturs_list_and_detail(self):
        resp = self.client.get(f"{BASE}/xojalik-konturs/", {"xojalik_location": str(self.location.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.data[0]), {"id", "kontur_raqami", "area_ga"})
        detail = self.client.get(f"{BASE}/xojalik-konturs/{resp.data[0]['id']}/").data
        for key in ("xojalik_location", "xojalik_name", "region_name", "latitude", "longitude", "bounds", "attributes", "geojson"):
            self.assertIn(key, detail)
        self.assertEqual(detail["xojalik_name"], self.ref.xojalik.name)


class BoundaryValidationTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.client = auth(self.client, make_user("billing", "billing_super"))

    def post(self, boundary, **overrides):
        payload = contract_payload(self.ref, boundary_geojson=boundary, **overrides)
        return self.client.post(URL, payload, format="json")

    def test_overlap_with_active_contract_is_rejected(self):
        first = self.post(square(72.0, 40.0), contract_number="A", pinfl="11111111111111")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertTrue(first.data["has_boundary"])

        same = self.post(square(72.0, 40.0), contract_number="B", pinfl="22222222222222")
        self.assertEqual(same.status_code, 400)
        self.assertIn("allaqachon", same.data["errors"]["contract"]["boundary_geojson"])

        overlapping = self.post(square(72.005, 40.005), contract_number="C", pinfl="33333333333333")
        self.assertEqual(overlapping.status_code, 400)
        self.assertIn("kirib ketmoqda", overlapping.data["errors"]["contract"]["boundary_geojson"])

        disjoint = self.post(square(72.5, 40.5), contract_number="D", pinfl="44444444444444")
        self.assertEqual(disjoint.status_code, 201, disjoint.data)

        # Faol bo'lmagan shartnoma chegarasi to'siq emas
        self.client.post(f"{URL}{first.data['id']}/status/", {"status": "inactive", "cancel_reason": "x"}, format="json")
        again = self.post(square(72.0, 40.0), contract_number="E", pinfl="55555555555555")
        self.assertEqual(again.status_code, 201, again.data)

    def test_boundary_must_intersect_xojalik_territory(self):
        make_location(self.ref, lon=72.0, lat=40.0, size=1.0)
        outside = self.post(square(75.0, 45.0), contract_number="A", pinfl="11111111111111")
        self.assertEqual(outside.status_code, 400)
        self.assertIn("o'rmon fondi", outside.data["errors"]["contract"]["boundary_geojson"])
        inside = self.post(square(72.1, 40.1), contract_number="B", pinfl="22222222222222")
        self.assertEqual(inside.status_code, 201, inside.data)

    def test_non_polygon_boundary_rejected_and_patch_checks_too(self):
        resp = self.post({"type": "Point", "coordinates": [72, 40]}, contract_number="A", pinfl="11111111111111")
        self.assertEqual(resp.status_code, 400)
        first = self.post(square(72.0, 40.0), contract_number="B", pinfl="22222222222222").data
        second = self.post(square(73.0, 41.0), contract_number="C", pinfl="33333333333333").data
        patch = self.client.patch(f"{URL}{second['id']}/", {"contract": {"boundary_geojson": square(72.0, 40.0)}}, format="json")
        self.assertEqual(patch.status_code, 400)
        own = self.client.patch(f"{URL}{first['id']}/", {"contract": {"boundary_geojson": square(72.0, 40.0)}}, format="json")
        self.assertEqual(own.status_code, 200, own.data)  # o'z chegarasi o'ziga to'siq emas


class ManagementCommandsTest(TestCase):
    def test_seed_billing_is_idempotent(self):
        out = io.StringIO()
        call_command("seed_billing", stdout=out)
        counts = (Region.objects.count(), District.objects.count(), Xojalik.objects.count(), Bolim.objects.count(),
                  LandType.objects.count(), ActivityType.objects.count(), PrivilegeType.objects.count())
        self.assertEqual(counts, (14, 206, 99, 293, 7, 23, 4))  # activity_types'da 1, bolimlar'da 2 ta takror
        self.assertEqual(Region.objects.get(code="1735").billing_id, 1)
        self.assertEqual(District.objects.get(code="1708209").name, "Ғаллаорол тумани")
        self.assertEqual(Xojalik.objects.get(name="Беруний ДЎХ").code, "23:02:06")
        self.assertIsNone(Xojalik.objects.get(name="Беруний ДЎХ").inn)
        call_command("seed_billing", stdout=io.StringIO())
        self.assertEqual((Xojalik.objects.count(), ActivityType.objects.count()), (99, 23))

    def test_seed_billing_migrates_old_short_codes_in_place(self):
        region = Region.objects.create(code="8", name="Жиззах вилояти", billing_id=4)
        district = District.objects.create(region=region, code="12", name="Ғаллаорол туман")
        call_command("seed_billing", stdout=io.StringIO())
        region.refresh_from_db()
        district.refresh_from_db()
        self.assertEqual(region.code, "1708")
        self.assertEqual((district.code, district.name), ("1708209", "Ғаллаорол тумани"))
        self.assertEqual(Region.objects.count(), 14)
        self.assertEqual(District.objects.filter(region=region).count(), 13)

    def test_seed_billing_merges_legacy_spelled_districts(self):
        call_command("seed_billing", stdout=io.StringIO())
        surxon = Region.objects.get(code="1722")
        official = District.objects.get(region=surxon, code="1722223")  # Шеробод тумани
        legacy = District.objects.create(region=surxon, code="13", name="Шерабад тумани")
        ref = make_reference(name="Сурхон ДЎХ")
        contract = Contract.objects.create(
            renter=Renter.objects.create(pinfl="12345678901234", full_name="Ijarachi"),
            xojalik=ref.xojalik, region=surxon, district=legacy, contract_date="2026-01-10",
            number="X-1", rent_area=1,
        )
        tashkent = Region.objects.get(code="1727")
        District.objects.filter(region=tashkent, code="1727250").delete()
        renamed = District.objects.create(region=tashkent, code="10", name="Пскент тумани")

        call_command("seed_billing", stdout=io.StringIO())

        self.assertFalse(District.objects.filter(pk=legacy.pk).exists())
        contract.refresh_from_db()
        self.assertEqual(contract.district, official)
        renamed.refresh_from_db()
        self.assertEqual((renamed.code, renamed.name), ("1727250", "Пискент тумани"))
        self.assertEqual(District.objects.filter(region=tashkent, name="Пискент тумани").count(), 1)

    def test_import_xojalik_locations(self):
        ref = make_reference(name="Андижон ДЎХ")
        record = {
            "name": "Андижон ДЎХ", "region_id": 2, "region_name": "Андижон вилояти",
            "latitude": 40.69, "longitude": 72.69, "bounds": [[40.3, 71.5], [40.9, 73.1]], "area_ga": 10459.29,
            "parcel_count": 2, "boundary_geojson": {"type": "Feature", "geometry": square(72, 40), "properties": {}},
            "konturlar": [
                {"seq": 0, "kontur_raqami": "9216", "raqami_num": 9216, "latitude": 40.7, "longitude": 72.3,
                 "bounds": [[40.7, 72.3], [40.71, 72.31]], "area_ga": 5.55, "attributes": {"x": "1"}, "geojson": square(72.3, 40.7)},
                {"seq": 1, "kontur_raqami": "", "raqami_num": None, "latitude": 40.8, "longitude": 72.4,
                 "bounds": None, "area_ga": 1, "attributes": None, "geojson": square(72.4, 40.8)},
            ],
        }
        unknown_region = dict(record, name="Noma'lum", region_id=999)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                json.dump([record, unknown_region], fh)

            out = io.StringIO()
            call_command("import_xojalik_locations", source=str(path), stdout=out)
            location = XojalikLocation.objects.get()
            self.assertEqual(location.xojalik, ref.xojalik)
            self.assertEqual(location.region, ref.region)
            self.assertEqual(location.konturlar.count(), 2)
            self.assertIn("o'tkazib yuborildi 1", out.getvalue())

            # --if-empty: jadval bo'sh emas -> hech narsa o'zgarmaydi
            record["konturlar"].pop()
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                json.dump([record], fh)
            call_command("import_xojalik_locations", source=str(path), if_empty=True, stdout=io.StringIO())
            self.assertEqual(location.konturlar.count(), 2)
            # qayta ishga tushirish: yangilanadi, yo'q konturlar o'chadi
            call_command("import_xojalik_locations", source=str(path), stdout=io.StringIO())
            self.assertEqual(XojalikLocation.objects.count(), 1)
            self.assertEqual(location.konturlar.count(), 1)

    def test_create_billing_user(self):
        call_command("create_billing_user", email="Billing@Example.com", password="StrongPass123!", first_name="B", last_name="U", stdout=io.StringIO())
        from apps.users.models import CustomUser

        user = CustomUser.objects.get(email="billing@example.com")
        self.assertEqual(user.role, "billing_user")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["billing_user"])
