"""Ma'lumotnoma API: mahallalar, yetkazib beruvchilar, katalog, kalendar (TZ §3, §8)."""
from datetime import date

from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.yashil.models import CalendarDay, CatalogItem, ObjectType, Season, YashilMembership
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_item, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)

T = YashilMembership.MemberType


class SuppliersForMahallaTest(APITestCase):
    def setUp(self):
        self.r = make_region()
        self.d = make_district(self.r)
        self.mahalla = make_mahalla(self.d)
        self.user = make_user("m", role="ym_mahalla")
        self.cab = member(self.user, T.MAHALLA, mahalla=self.mahalla)
        self.client = auth(self.client, self.user)

    def test_primary_forest_supplier_and_alternatives(self):
        f1 = make_forest("Асосий хўжалик")
        f2 = make_forest("Бошқа хўжалик")
        make_forest("Нофаол хўжалик", is_active_supplier=False)
        assign_forest(self.mahalla, f1)
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{self.mahalla.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["forest"]["primary"]["id"], str(f1.pk))
        self.assertEqual({x["id"] for x in res.data["forest"]["alternatives"]}, {str(f2.pk)})
        self.assertIsNone(res.data["forest"]["message"])

    def test_missing_assignment_gives_message_not_a_guess(self):
        make_forest("Қандайдир хўжалик")
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{self.mahalla.pk}/")
        self.assertIsNone(res.data["forest"]["primary"])
        self.assertEqual(res.data["forest"]["message"], "Хўжалик бириктирилмаган")
        self.assertEqual(len(res.data["forest"]["alternatives"]), 1)

    def test_dm_list_filtered_by_service_area_and_union_route(self):
        dm_here, p = make_dm("Андижон ДМ")
        p.service_regions.add(self.r)
        dm_far, p2 = make_dm("Бухоро ДМ")
        p2.service_regions.add(make_region("1706", "Бухоро вилояти"))
        dm_all, _ = make_dm("Республика ДМ")
        unit = make_union(self.d)
        route_union(self.mahalla, unit)
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{self.mahalla.pk}/")
        self.assertEqual({x["id"] for x in res.data["dm"]["options"]}, {str(dm_here.pk), str(dm_all.pk)})
        self.assertEqual(res.data["union"]["id"], str(unit.pk))

    def test_other_mahalla_is_forbidden_for_mahalla_cabinet(self):
        other = make_mahalla(self.d, "Бошқа маҳалла")
        res = self.client.get(f"{BASE}/suppliers/for-mahalla/{other.pk}/")
        self.assertEqual(res.status_code, 404)


class CatalogApiTest(APITestCase):
    def setUp(self):
        self.d = make_district(make_region())
        self.mahalla = make_mahalla(self.d)
        self.user = make_user("m", role="ym_mahalla")
        member(self.user, T.MAHALLA, mahalla=self.mahalla)
        self.client = auth(self.client, self.user)
        self.forest = make_forest()
        self.dm, _ = make_dm()
        make_item("ASH", "Шумтол кўчати", "forest", "seedling", "tup", attributes={"age": "2-3", "height": "1-1.5 m"})
        make_item("MUL", "Мульча", "forest", "mulch", "kg")
        make_item("BIO", "Биогумус", "dm", "fertilizer", "kg")
        make_item("PRT", "Ҳимоя хизмати", "dm", "protection_service", "daraxt", item_type="service")
        make_item("OLD", "Эски", "dm", "equipment", "dona", is_active=False)

    def test_catalog_by_supplier_type(self):
        res = self.client.get(f"{BASE}/catalog/?supplier={self.forest.pk}")
        self.assertEqual([x["code"] for x in res.data], ["ASH", "MUL"])
        self.assertEqual(res.data[0]["precision"], 0)
        self.assertEqual(res.data[0]["attributes"]["age"], "2-3")
        res = self.client.get(f"{BASE}/catalog/?supplier={self.dm.pk}")
        self.assertEqual({x["code"] for x in res.data}, {"BIO", "PRT"})
        self.assertEqual({x["item_type"] for x in res.data}, {"goods", "service"})

    def test_catalog_without_supplier_returns_all_active(self):
        res = self.client.get(f"{BASE}/catalog/")
        self.assertEqual(len(res.data), 4)


class ReferenceListsTest(APITestCase):
    def setUp(self):
        self.r = make_region()
        self.d1 = make_district(self.r, "1703202", "Андижон тумани")
        self.d2 = make_district(self.r, "1703203", "Асака тумани")
        self.m1 = make_mahalla(self.d1, "Боғистон")
        self.m2 = make_mahalla(self.d2, "Навбаҳор")
        self.unit = make_union(self.d1)
        route_union(self.m1, self.unit)

    def test_union_sees_only_routed_mahallas_and_can_filter_by_district(self):
        user = make_user("u", role="ym_union")
        member(user, T.UNION, union_unit=self.unit)
        res = auth(self.client, user).get(f"{BASE}/reference/mahallas/")
        self.assertEqual([x["name"] for x in res.data["results"]], ["Боғистон"])
        res = self.client.get(f"{BASE}/reference/mahallas/?district={self.d2.pk}")
        self.assertEqual(res.data["results"], [])

    def test_observer_search(self):
        user = make_user("o", role="ym_observer")
        member(user, T.OBSERVER, can_prepare=False, can_sign=False)
        res = auth(self.client, user).get(f"{BASE}/reference/mahallas/?q=навб")
        self.assertEqual([x["name"] for x in res.data["results"]], ["Навбаҳор"])

    def test_seasons_and_object_types(self):
        Season.objects.create(year=2027, kind="spring", date_from=date(2027, 3, 1), date_to=date(2027, 5, 31))
        ObjectType.objects.create(code="street", name_cyr="Кўча/йўл бўйи", name_lat="Ko'cha/yo'l bo'yi", order=1)
        ObjectType.objects.create(code="other", name_cyr="Бошқа", name_lat="Boshqa", requires_note=True, order=9)
        user = make_user("o2", role="ym_observer")
        member(user, T.OBSERVER, can_prepare=False, can_sign=False)
        auth(self.client, user)
        self.assertEqual(self.client.get(f"{BASE}/reference/seasons/").data[0]["label_cyr"], "2027 баҳор")
        types = self.client.get(f"{BASE}/reference/object-types/").data
        self.assertEqual([t["requires_note"] for t in types], [False, True])


class CalendarApiTest(APITestCase):
    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        user = make_user("c", role="ym_mahalla")
        member(user, T.MAHALLA, mahalla=make_mahalla(d))
        self.client = auth(self.client, user)

    def test_due_dates_respect_calendar(self):
        CalendarDay.objects.create(date=date(2027, 1, 14), kind="holiday", note="Байрам")
        res = self.client.get(f"{BASE}/calendar/due/?start=2027-01-11")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["review_due"], "2027-01-15")
        self.assertEqual(res.data["delivery_due"], "2027-01-26")
        res = self.client.get(f"{BASE}/calendar/?year=2027")
        self.assertEqual(res.data[0]["date"], "2027-01-14")

    def test_bad_start_date_is_400_with_contract(self):
        res = self.client.get(f"{BASE}/calendar/due/?start=11.01.2027")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error_code"], "invalid_format")
        self.assertEqual(res.data["field"], "start")
