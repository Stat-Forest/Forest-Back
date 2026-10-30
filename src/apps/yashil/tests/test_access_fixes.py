"""Ko'lam va vakolat chegaralari (rol-vakolat matritsasini tuzishda topilgan holatlar; TZ §2, §17.2)."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.test import APITestCase

from apps.base.admin import admin_site as site
from apps.yashil.models import ActAttachment, Order, OrderAttachment, OrderState, YashilMembership
from apps.yashil.services import acts as act_service
from apps.yashil.services import cancel as cancel_service
from apps.yashil.services import transitions as tr
from apps.yashil.services.transitions import TransitionError
from apps.yashil.tests._common import (
    BASE, assign_forest, auth, make_district, make_dm, make_forest, make_mahalla, make_region, make_union,
    make_user, member, route_union,
)
from apps.yashil.tests.test_cancel import NOW, CancelBase

T = YashilMembership.MemberType


class ModuleAdminWithoutCabinetTest(APITestCase):
    """Kabinetsiz modul ma'muri buyurtma oqimidagi amalni bajarmaydi — 403, server xatosi emas."""

    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        mahalla = make_mahalla(d)
        forest = make_forest(); assign_forest(mahalla, forest)
        unit = make_union(d); route_union(mahalla, unit)
        m_cab = member(make_user("m", role="ym_mahalla"), T.MAHALLA, mahalla=mahalla)
        self.order = Order.objects.create(mahalla=mahalla, route="forest", supplier_org=forest, union_unit=unit,
                                          created_by_membership=m_cab, number="YM-2027-000001", state=OrderState.UNION_NEW)
        self.admin = make_user("adm", role="super_admin")

    def test_transition_endpoints_return_403(self):
        auth(self.client, self.admin)
        for i, action in enumerate(("review", "forward", "return", "accept")):
            with self.subTest(action=action):
                res = self.client.post(f"{BASE}/orders/{self.order.pk}/{action}/", {"comment": "x", "executor_name": "x"},
                                       format="json", HTTP_IDEMPOTENCY_KEY=f"k{i}")
                self.assertEqual(res.status_code, 403, res.data)
                self.assertEqual(res.data["error_code"], "forbidden")

    def test_services_reject_missing_cabinet(self):
        for call in (lambda: tr.start_review(self.order, None), lambda: tr.forward(self.order, None),
                     lambda: tr.return_order(self.order, None, reason_code="", comment="x"),
                     lambda: tr.accept(self.order, None, executor_name="x")):
            with self.assertRaises(TransitionError) as cm:
                call()
            self.assertEqual(cm.exception.status, 403)


class CancelRejectRequiresPrepareTest(CancelBase):
    def test_other_party_without_prepare_right_cannot_reject(self):
        self.accept()
        req = cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="x")
        viewer = member(make_user("s2", role="tashkilot_hodimi", organization=self.forest), T.SUPPLIER,
                        organization=self.forest, can_prepare=False, can_sign=False)
        with self.assertRaises(TransitionError) as cm:
            cancel_service.reject_cancel(req, viewer, note="Йўқ")
        self.assertEqual((cm.exception.status, cm.exception.code), (403, "cannot_prepare"))
        req.refresh_from_db()
        self.assertEqual(req.status, "requested")

    def test_act_cannot_be_created_while_cancel_request_open(self):
        self.accept()
        cancel_service.request_cancel(self.order, self.m_cab, lines=[], reason="x")
        with self.assertRaises(TransitionError) as cm, patch("django.utils.timezone.now", return_value=NOW):
            act_service.create_act(self.order, self.s_cab, delivery_date=date(2027, 1, 11),
                                   lines=[{"order_line": self.l_ash, "qty": Decimal("10")}])
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "cancel_pending"))
        self.assertFalse(self.order.acts.exists())


class RegionalObserverStockScopeTest(APITestCase):
    """Hududiy kuzatuvchi faqat o'z ko'lamidagi mahallalarga xizmat qiluvchi yetkazib beruvchilar omborini ko'radi."""

    def setUp(self):
        cache.clear()
        d = make_district(make_region())
        far = make_district(make_region("1735", "Қорақалпоғистон"), "1735401", "Нукус тумани")
        self.forest = make_forest(); assign_forest(make_mahalla(d), self.forest)
        self.far_forest = make_forest("Узоқ хўжалик"); assign_forest(make_mahalla(far, "Узоқ маҳалла"), self.far_forest)
        self.dm, p = make_dm(); p.service_regions.add(d.region)
        self.far_dm, fp = make_dm("Узоқ ДМ"); fp.service_regions.add(far.region)
        self.user = make_user("o", role="ym_observer")
        self.cab = member(self.user, T.OBSERVER, can_prepare=False, can_sign=False, observer_scope={"regions": ["1703"]})
        auth(self.client, self.user, self.cab)

    def test_organizations_list_limited_to_scope(self):
        res = self.client.get(f"{BASE}/stock/organizations/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual({r["id"] for r in res.data["results"]}, {str(self.forest.pk), str(self.dm.pk)})

    def test_out_of_scope_stock_is_not_found(self):
        for org in (self.far_forest, self.far_dm):
            for url in ("stock/", "stock/movements/"):
                with self.subTest(org=org.name, url=url):
                    res = self.client.get(f"{BASE}/{url}", {"organization": str(org.pk)})
                    self.assertEqual(res.status_code, 404, res.data)
        res = self.client.get(f"{BASE}/stock/", {"organization": str(self.forest.pk)})
        self.assertEqual(res.status_code, 200, res.data)

    def test_republic_observer_sees_all(self):
        self.cab.observer_scope = {}
        self.cab.save()
        res = self.client.get(f"{BASE}/stock/organizations/")
        self.assertEqual(len(res.data["results"]), 4)


class AttachmentAdminDeleteTest(APITestCase):
    def test_attachments_cannot_be_deleted_in_django_admin(self):
        request = RequestFactory().get("/")
        request.user = make_user("su", role="super_admin", is_superuser=True, is_staff=True)
        for model in (OrderAttachment, ActAttachment):
            self.assertFalse(site._registry[model].has_delete_permission(request))
