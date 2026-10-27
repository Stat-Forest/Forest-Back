"""
2026-10-27 xavfsizlik ko'rigi: A4 maskani chetlab o'tish yo'llari yopildi — tarix
(eski billing `legacy` JSON, "F.I.Sh. (JSHSHIR)"), shartnoma tafsilotidagi fayl
havolalari, JSHSHIR bo'yicha qism qidiruv; billing_user boshqa xo'jalik ijarachisini
JSHSHIR/INN terib ola olmaydi (B7/H2); MIB qayta yuborish faqat superuser.
"""
import json
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.billing._tests_common import BASE, auth, contract_payload, make_user
from apps.billing.admin import MibPushLogAdmin
from apps.billing.models import Contract, ContractFile, ContractHistory, MibPushLog, Renter
from apps.billing.services.contract_writer import RENTER_MISMATCH_MESSAGE
from apps.billing.test_scope import BillingScopeTestBase

URL = f"{BASE}/contracts/"
OWN_PINFL = "11111111111111"
FOREIGN_PINFL = "22222222222222"


class HistoryAndFilesMaskTest(BillingScopeTestBase):
    def setUp(self):
        super().setUp()
        self.hodim = make_user("hodim", "tashkilot_hodimi")
        ContractHistory.objects.create(
            contract=self.own, reason=ContractHistory.Reason.UPDATED,
            data={"legacy_reason": "Ijarachi o'zgartirildi",
                  "legacy": {"rented_user": {"pinfl": "33333333333333", "passport": "AA1234567"}}},
        )
        ContractFile.objects.create(contract=self.own, file="documents/billing/contracts/2026/10/scan.pdf")

    def _get(self, user, path):
        resp = auth(self.client_class(), user).get(path)
        self.assertEqual(resp.status_code, 200, resp.data)
        return resp

    def test_history_masked_for_non_pii_role(self):
        text = json.dumps(self._get(self.hodim, f"{URL}{self.own.id}/history/").data, ensure_ascii=False)
        self.assertNotIn(OWN_PINFL, text)
        self.assertNotIn("33333333333333", text)
        self.assertNotIn("AA1234567", text)
        self.assertIn("Test Renter (11**********11)", text)
        self.assertIn("Ijarachi o'zgartirildi", text)  # legacy_reason qoladi

    def test_history_full_for_pii_role(self):
        text = json.dumps(self._get(self.super, f"{URL}{self.own.id}/history/").data, ensure_ascii=False)
        self.assertIn(f"Test Renter ({OWN_PINFL})", text)
        self.assertIn("AA1234567", text)

    def test_detail_files_only_for_pii_roles(self):
        self.assertEqual(self._get(self.hodim, f"{URL}{self.own.id}/").data["files"], [])
        files = self._get(self.super, f"{URL}{self.own.id}/").data["files"]
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0]["file_url"])

    def test_partial_pinfl_search_only_for_pii_roles(self):
        def count(user, query):
            return self._get(user, f"{URL}?{query}").data["count"]

        for query in ("search=1111111", "stir=1111111"):
            with self.subTest(query=query):
                self.assertEqual(count(self.hodim, query), 0)
                self.assertEqual(count(self.super, query), 1)
        self.assertEqual(count(self.hodim, f"search={OWN_PINFL}"), 1)
        self.assertEqual(count(self.hodim, f"stir={OWN_PINFL}"), 1)


class OutOfScopeRenterTest(BillingScopeTestBase):
    def _payload(self, **renter):
        payload = contract_payload(self.ref, pinfl=FOREIGN_PINFL, contract_number="NEW-1")
        payload["renter"].update(renter)
        return payload

    def test_create_with_foreign_pinfl_needs_matching_identity(self):
        resp = self.as_user().post(URL, self._payload(full_name="Boshqa Odam"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["errors"]["renter"]["pinfl"], RENTER_MISMATCH_MESSAGE)
        self.assertFalse(Contract.objects.filter(contract_number="NEW-1").exists())

    def test_create_with_foreign_pinfl_and_same_name_links_existing(self):
        resp = self.as_user().post(URL, self._payload(full_name="  test   renter "), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(str(resp.data["renter"]["id"]), str(self.foreign.renter_id))

    def test_billing_super_unaffected(self):
        client = auth(self.client_class(), self.super)
        resp = client.post(URL, self._payload(full_name="Boshqa Odam"), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_update_cannot_overwrite_foreign_renter(self):
        # own ijarachisi umumiy bo'lsin (identity o'zgarsa boshqa ijarachi qidiriladi)
        self._create(self.super, self.ref, pinfl=OWN_PINFL, contract_number="OWN-2")
        client = self.as_user()
        resp = client.patch(f"{URL}{self.own.id}/",
                            {"renter": {"pinfl": FOREIGN_PINFL, "full_name": "Hack", "phone": "+998000000000"}},
                            format="json")
        self.assertEqual(resp.status_code, 400)
        foreign = Renter.objects.get(id=self.foreign.renter_id)
        self.assertEqual(foreign.full_name, "Test Renter")

        resp = client.patch(f"{URL}{self.own.id}/",
                            {"renter": {"pinfl": FOREIGN_PINFL, "full_name": "Test Renter", "phone": "+998000000000"}},
                            format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.own.refresh_from_db()
        self.assertEqual(self.own.renter_id, self.foreign.renter_id)
        foreign.refresh_from_db()
        self.assertEqual(foreign.phone, "+998901112233")  # boshqa xo'jalik ijarachisi o'zgarmadi


class MibResendPermissionTest(BillingScopeTestBase):
    def test_resend_requires_superuser(self):
        MibPushLog.objects.create(contract=self.own, payload={}, payload_hash="x", dtl="2026-10-30")
        model_admin = MibPushLogAdmin(MibPushLog, AdminSite())
        request = RequestFactory().post("/")
        for user, calls in ((make_user("staffview", "super_admin"), 0),):
            request.user = user
            with mock.patch("apps.billing.admin.mib_push.push_contract") as push, \
                    mock.patch.object(model_admin, "message_user"):
                model_admin.resend(request, MibPushLog.objects.all())
            self.assertEqual(push.call_count, calls)
        request.user = make_user("root", "super_admin", is_superuser=True)
        with mock.patch("apps.billing.admin.mib_push.push_contract") as push, \
                mock.patch.object(model_admin, "message_user"):
            model_admin.resend(request, MibPushLog.objects.all())
        self.assertEqual(push.call_count, 1)
