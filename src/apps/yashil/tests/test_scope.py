"""Kabinet ko'lami: kim qaysi mahallalarni ko'radi (TZ §2 jadval)."""
from django.test import TestCase

from apps.yashil.models import YashilMembership
from apps.yashil.services.scope import visible_mahalla_ids
from apps.yashil.tests._common import (
    assign_forest, make_district, make_dm, make_forest, make_mahalla, make_region, make_union, make_user, member,
    route_union,
)

T = YashilMembership.MemberType


class VisibleMahallasTest(TestCase):
    def setUp(self):
        self.r1 = make_region("1703", "Андижон вилояти")
        self.r2 = make_region("1706", "Бухоро вилояти")
        self.d1 = make_district(self.r1, "1703202", "Андижон тумани")
        self.d2 = make_district(self.r1, "1703203", "Асака тумани")
        self.d3 = make_district(self.r2, "1706204", "Бухоро тумани")
        self.m1 = make_mahalla(self.d1, "M1")
        self.m2 = make_mahalla(self.d1, "M2")
        self.m3 = make_mahalla(self.d2, "M3")
        self.m4 = make_mahalla(self.d3, "M4")

    def ids(self, m):
        return visible_mahalla_ids(m)

    def test_mahalla_member_sees_only_own(self):
        m = member(make_user("a"), T.MAHALLA, mahalla=self.m1)
        self.assertEqual(self.ids(m), {self.m1.pk})

    def test_union_member_sees_routed_mahallas_only(self):
        unit = make_union(self.d1)
        route_union(self.m1, unit)
        route_union(self.m2, unit)
        route_union(self.m3, make_union(self.d2, "Асака уюшмаси"))
        m = member(make_user("u"), T.UNION, union_unit=unit)
        self.assertEqual(self.ids(m), {self.m1.pk, self.m2.pk})

    def test_forest_supplier_sees_assigned_mahallas(self):
        f = make_forest()
        assign_forest(self.m1, f)
        assign_forest(self.m3, f)
        m = member(make_user("f"), T.SUPPLIER, organization=f)
        self.assertEqual(self.ids(m), {self.m1.pk, self.m3.pk})

    def test_dm_supplier_sees_mahallas_in_service_area(self):
        dm, profile = make_dm()
        profile.service_districts.add(self.d2)
        profile.service_regions.add(self.r2)
        m = member(make_user("d"), T.SUPPLIER, organization=dm)
        self.assertEqual(self.ids(m), {self.m3.pk, self.m4.pk})

    def test_dm_without_service_area_sees_everything(self):
        dm, _ = make_dm()
        m = member(make_user("d2"), T.SUPPLIER, organization=dm)
        self.assertIsNone(self.ids(m))

    def test_observer_scope_republic_region_district(self):
        rep = member(make_user("o1"), T.OBSERVER, can_prepare=False, can_sign=False)
        self.assertIsNone(self.ids(rep))
        reg = member(make_user("o2"), T.OBSERVER, can_prepare=False, can_sign=False, observer_scope={"regions": ["1703"]})
        self.assertEqual(self.ids(reg), {self.m1.pk, self.m2.pk, self.m3.pk})
        dis = member(make_user("o3"), T.OBSERVER, can_prepare=False, can_sign=False, observer_scope={"districts": ["1703203"]})
        self.assertEqual(self.ids(dis), {self.m3.pk})
