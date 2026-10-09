"""Shartnoma CRUD, nested bo'limlar, holat, yillik summalar, filtrlar, summary/counts/geo-list."""
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user
from apps.billing.models import Contract, ContractHistory, ContractLand, Renter

URL = f"{BASE}/contracts/"


class ContractApiTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.user = make_user("billing", "billing_super")
        self.client = auth(self.client, self.user)

    def create(self, **overrides):
        resp = self.client.post(URL, contract_payload(self.ref, **overrides), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data


class ContractCreateTest(ContractApiTestBase):
    def test_create_full_payload(self):
        data = self.create()
        contract = Contract.objects.get(id=data["id"])

        self.assertEqual(contract.number, "23:02:06-1")
        self.assertEqual(data["number"], "23:02:06-1")
        self.assertEqual(data["contract_date"], "10.01.2026")
        self.assertEqual(data["expired_date"], "10.01.2027")  # default +1 yil
        self.assertEqual(data["status"], "active")
        # ijarachi yaratildi
        self.assertEqual(Renter.objects.count(), 1)
        self.assertEqual(data["renter"]["pinfl"], "12345678901234")
        self.assertEqual(data["renter"]["per_adr"], "Andijon")
        # yillik summalar -> totals
        self.assertEqual(data["rent_amount"], "1100.00")
        self.assertEqual(data["paid_amount"], "500.00")
        self.assertEqual(data["penalty_amount"], "10.00")
        self.assertEqual(data["debt"], "600.00")
        self.assertEqual(len(data["yearly_amounts"]), 2)
        self.assertEqual(data["yearly_amounts"][0]["debt_amount"], "300.00")
        # nested
        self.assertEqual(data["lands"][0]["type_name"], "Чўл")
        self.assertEqual(data["activities"][0]["area"], "7.50")
        self.assertEqual(str(data["privileges"][0]["type"]), str(self.ref.privilege_type.id))
        self.assertEqual(data["action"]["vacancy"], "3.00")
        self.assertEqual(data["action"]["products"][0]["product_export"], "Yong'oq")
        self.assertEqual(data["files"], [])
        self.assertEqual(data["xojalik_name"], self.ref.xojalik.name)
        self.assertEqual(data["bolim_name"], "Markaziy")
        self.assertFalse(data["has_boundary"])
        # tarix
        self.assertEqual(contract.history.get().reason, ContractHistory.Reason.CREATED)

    def test_second_contract_increments_number_and_reuses_renter(self):
        self.create()
        data = self.create(contract_number="SH-2")
        self.assertEqual(data["number"], "23:02:06-2")
        self.assertEqual(Renter.objects.count(), 1)

    def test_iso_dates_accepted(self):
        data = self.create(contract_date="2026-02-01", expired_date="2027-02-01")
        self.assertEqual(data["contract_date"], "01.02.2026")

    def test_missing_contract_fields(self):
        payload = contract_payload(self.ref)
        del payload["contract"]["contract_date"]
        del payload["contract"]["xojalik"]
        resp = self.client.post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("contract_date", resp.data["errors"]["contract"])
        self.assertIn("xojalik", resp.data["errors"]["contract"])
        self.assertEqual(Contract.objects.count(), 0)

    def test_renter_requires_pinfl_or_stir(self):
        payload = contract_payload(self.ref)
        payload["renter"] = {"full_name": "No id"}
        resp = self.client.post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pinfl", resp.data["errors"]["renter"])

    def test_rent_area_required_and_positive(self):
        for value in ("", "0"):
            resp = self.client.post(URL, contract_payload(self.ref, rent_area=value), format="json")
            self.assertEqual(resp.status_code, 400, value)
            self.assertIn("rent_area", resp.data["errors"]["contract"])
        payload = contract_payload(self.ref)
        payload["contract"].pop("rent_area")
        resp = self.client.post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("rent_area", resp.data["errors"]["contract"])
        self.assertEqual(Contract.objects.count(), 0)

    def test_duplicate_contract_number_rejected(self):
        self.create()
        resp = self.client.post(URL, contract_payload(self.ref, pinfl="22222222222222"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("contract_number", resp.data["errors"]["contract"])

    def test_bolim_must_belong_to_xojalik(self):
        other = make_reference(code="11:11:11", inn="987654321", name="Boshqa DÒX")
        resp = self.client.post(URL, contract_payload(self.ref, bolim=str(other.bolim.id)), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("bolim", resp.data["errors"]["contract"])

    def test_type_by_name_rejected_when_unknown(self):
        payload = contract_payload(self.ref)
        payload["lands"] = [{"type": "yo'q tur", "area": "1"}]
        resp = self.client.post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("yo'q tur", resp.data["errors"]["lands"])
        self.assertEqual(Contract.objects.count(), 0)  # atomik


class ContractUpdateTest(ContractApiTestBase):
    def setUp(self):
        super().setUp()
        self.data = self.create()
        self.contract = Contract.objects.get(id=self.data["id"])

    def test_patch_nested_update_delete_create(self):
        land_id = self.data["lands"][0]["id"]
        product_id = self.data["action"]["products"][0]["id"]
        payload = {
            "contract": {"cadastral_number": "KAD-1", "rent_area": "20.00", "status": "inactive"},
            "renter": {"phone": "+998900000000"},
            "lands": [
                {"id": land_id, "type": str(self.ref.land_type.id), "area": "6.00"},
                {"type": str(self.ref.land_type.id), "area": "1.00"},
            ],
            "activities": [{"id": self.data["activities"][0]["id"], "delete": True}],
            "action": {"vacancy": "5"},
            "action_products": [{"id": product_id, "delete": True}, {"product_export": "Bodom", "export_amount": "1"}],
            "yearly_amounts": [{"year": 2026, "calculated_amount": "900", "paid_amount": "300"}],
        }
        resp = self.client.patch(f"{URL}{self.contract.id}/", payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.data
        self.assertEqual(data["cadastral_number"], "KAD-1")
        self.assertEqual(data["rent_area"], "20.00")
        self.assertEqual(data["status"], "active")  # status PATCH'da qabul qilinmaydi
        self.assertEqual(data["renter"]["phone"], "+998900000000")
        self.assertEqual(len(data["lands"]), 2)
        self.assertEqual(ContractLand.objects.get(id=land_id).area, Decimal("6.00"))
        self.assertEqual(data["activities"], [])
        self.assertEqual(data["action"]["vacancy"], "5.00")
        self.assertEqual([p["product_export"] for p in data["action"]["products"]], ["Bodom"])
        # 2026 yangilandi (update_or_create), totals qayta hisoblandi: 500 + 900
        self.assertEqual(data["rent_amount"], "1400.00")
        self.assertEqual(data["paid_amount"], "500.00")
        self.assertEqual(self.contract.history.filter(reason=ContractHistory.Reason.UPDATED).count(), 1)

    def test_patch_unknown_nested_id_is_rejected(self):
        other = Contract.objects.get(id=self.create(contract_number="SH-9", pinfl="33333333333333")["id"])
        foreign_land = other.lands.first()
        resp = self.client.patch(
            f"{URL}{self.contract.id}/",
            {"lands": [{"id": str(foreign_land.id), "type": str(self.ref.land_type.id), "area": "1"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("lands", resp.data["errors"])

    def test_status_change_requires_reason(self):
        resp = self.client.post(f"{URL}{self.contract.id}/status/", {"status": "inactive"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cancel_reason", resp.data["errors"]["contract"])

        resp = self.client.post(f"{URL}{self.contract.id}/status/", {"status": "inactive", "cancel_reason": "Muddati tugadi"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["status"], "inactive")
        self.assertEqual(resp.data["cancel_reason"], "Muddati tugadi")
        self.assertEqual(resp.data["canceled_date"], timezone.localdate().strftime("%d.%m.%Y"))

        resp = self.client.post(f"{URL}{self.contract.id}/status/", {"status": "active"}, format="json")
        self.assertEqual(resp.data["status"], "active")
        self.assertIsNone(resp.data["canceled_date"])
        self.assertIsNone(resp.data["cancel_reason"])
        self.assertEqual(self.contract.history.filter(reason=ContractHistory.Reason.STATUS_CHANGED).count(), 2)

    def test_yearly_amounts_endpoint(self):
        resp = self.client.patch(
            f"{URL}{self.contract.id}/yearly-amounts/",
            {"yearly_amounts": [{"year": 2024, "contract_amount": "100", "calculated_amount": "100", "paid_amount": "100"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data["yearly_amounts"]), 3)
        self.assertEqual(resp.data["rent_amount"], "1200.00")
        self.assertEqual(resp.data["paid_amount"], "600.00")
        self.assertEqual(resp.data["debt"], "600.00")
        self.assertEqual(self.contract.history.filter(reason=ContractHistory.Reason.YEARLY_UPDATED).count(), 1)

    def test_change_renter(self):
        new_renter = Renter.objects.create(stir="111111111", full_name="Yuridik", is_legal_entity=True)
        resp = self.client.post(f"{URL}{self.contract.id}/change-renter/", {"renter": str(new_renter.id)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(str(resp.data["renter"]["id"]), str(new_renter.id))
        self.assertTrue(resp.data["is_entity"])
        history = self.client.get(f"{URL}{self.contract.id}/history/").data
        self.assertEqual(history[0]["reason"], ContractHistory.Reason.RENTER_CHANGED)
        self.assertEqual(history[0]["executor_name"], "T Billing")
        self.assertIn("renter", history[0]["data"]["changes"])

    def test_detail_shape(self):
        resp = self.client.get(f"{URL}{self.contract.id}/")
        self.assertEqual(resp.status_code, 200)
        for key in ("boundary_geojson", "cadastral_number", "circle", "section", "counter", "massive", "auction_date",
                    "exemptioned_date", "is_entity", "yearly_amounts", "lands", "activities", "privileges", "action",
                    "files", "days_remaining", "is_expired", "files_count"):
            self.assertIn(key, resp.data)
        self.assertIn("is_legal_entity", resp.data["renter"])


class ContractListAndStatsTest(ContractApiTestBase):
    def setUp(self):
        super().setUp()
        self.a = self.create()  # 1100/500 -> qarzdor
        self.b = self.create(contract_number="SH-2", pinfl="22222222222222", latitude="", longitude="")
        self.b_obj = Contract.objects.get(id=self.b["id"])
        self.b_obj.yearly_amounts.all().delete()
        Contract.objects.filter(id=self.b_obj.id).update(rent_amount=100, paid_amount=100, status="inactive")

    def test_list_pagination_and_fields(self):
        resp = self.client.get(URL, {"per_page": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.data), {"count", "next", "previous", "results"})
        self.assertEqual(resp.data["count"], 2)
        row = resp.data["results"][0]
        for key in ("id", "number", "contract_number", "status", "xojalik_name", "xojalik_inn", "renter", "debt",
                    "has_boundary", "files_count", "days_remaining", "is_expired", "created_at", "region_name"):
            self.assertIn(key, row)
        self.assertEqual(set(row["renter"]), {"id", "full_name", "pinfl", "stir", "phone", "passport"})

    def test_filters(self):
        def ids(**params):
            return {str(r["id"]) for r in self.client.get(URL, params).data["results"]}

        a, b = str(self.a["id"]), str(self.b["id"])
        self.assertEqual(ids(status="active"), {a})
        self.assertEqual(ids(status="inactive"), {b})
        self.assertEqual(len(ids(status="all")), 2)
        self.assertEqual(ids(debtors="1"), {a})
        self.assertEqual(ids(stir="2222222"), {b})
        self.assertEqual(ids(number="SH-2"), {b})
        self.assertEqual(ids(search="23:02:06-1"), {a})
        self.assertEqual(ids(region=str(self.ref.region.id)), {a, b})
        self.assertEqual(ids(from_date="11.01.2026"), set())
        self.assertEqual(len(ids(from_date="2026-01-01", to_date="31.12.2026")), 2)
        ordered = [str(r["id"]) for r in self.client.get(URL, {"ordering": "-rent_amount"}).data["results"]]
        self.assertEqual(ordered[0], a)

    def test_summary(self):
        resp = self.client.get(f"{URL}summary/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_count"], 2)
        self.assertEqual(resp.data["total_rent_area"], "25.00")
        self.assertEqual(resp.data["total_rent_amount"], "1200.00")
        self.assertEqual(resp.data["total_paid_amount"], "600.00")
        self.assertEqual(resp.data["total_debt"], "600.00")
        by_year = self.client.get(f"{URL}summary/", {"year": 2026}).data
        self.assertEqual(by_year["total_count"], 2)
        self.assertEqual(by_year["total_rent_amount"], "600.00")
        self.assertEqual(by_year["total_penalty_amount"], "10.00")
        self.assertEqual(self.client.get(f"{URL}summary/", {"year": 2019}).data["total_rent_amount"], "0.00")

    def test_counts(self):
        resp = self.client.get(f"{URL}counts/", {"status": "inactive"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"all": 2, "active": 1, "inactive": 1, "added_today": {"all": 2, "active": 1, "inactive": 1}})

    def test_geo_list(self):
        resp = self.client.get(f"{URL}geo-list/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)  # faqat faol va joylashuvi bor
        row = resp.data["results"][0]
        self.assertEqual(str(row["id"]), str(self.a["id"]))
        self.assertEqual(row["latitude"], 40.7)
        self.assertEqual(row["debt"], 600.0)
        self.assertEqual(row["activity_name"], "ўрмон барпо қилиш")
        self.assertEqual(self.client.get(f"{URL}geo-list/", {"status": "all"}).data["count"], 1)  # b'da koordinata yo'q

    def test_renters_and_reference_lists(self):
        resp = self.client.get(f"{BASE}/renters/", {"search": "Test"})
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(resp.data["results"][0]["contracts_count"], 1)
        self.assertIsInstance(self.client.get(f"{BASE}/regions/").data, list)
        self.assertEqual(self.client.get(f"{BASE}/districts/", {"region": str(self.ref.region.id)}).data[0]["code"], "1703202")
        xojaliklar = self.client.get(f"{BASE}/xojaliklar/", {"search": "Test"}).data
        self.assertEqual(xojaliklar[0]["region_name"], "Андижон вилояти")
        bolimlar = self.client.get(f"{BASE}/bolimlar/", {"region": str(self.ref.region.id)}).data
        self.assertEqual(bolimlar[0]["xojalik_name"], self.ref.xojalik.name)
        self.assertIn("month", self.client.get(f"{BASE}/privilege-types/").data[0])
        self.assertIn("parent_name", self.client.get(f"{BASE}/land-types/").data[0])
