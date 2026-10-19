"""
Audit A4/B7: ijarachilarning shaxsiy ma'lumotlari (PINFL, pasport, telefon, manzil)
faqat billing rollari, super_admin va rahbariyat uchun; qolgan rollar billing
monitoringini ko'radi, lekin PII maskalangan. Ro'yxat/eksport/fayllar — yopiq.
"""
import json

from apps.billing._tests_common import BASE, auth, make_user
from apps.billing.models import Contract
from apps.billing.test_scope import BillingScopeTestBase

URL = f"{BASE}/contracts/"
OWN_PINFL = "11111111111111"
PHONE = "+998901112233"


class RenterPIIAccessTest(BillingScopeTestBase):
    def setUp(self):
        super().setUp()
        self.hodim = make_user("hodim", "tashkilot_hodimi")
        self.rahbariyat = make_user("rahbariyat", "rahbariyat")

    def _text(self, resp):
        self.assertEqual(resp.status_code, 200)
        return json.dumps(resp.data, ensure_ascii=False, default=str)

    def test_non_billing_role_cannot_list_renters_export_or_files(self):
        client = auth(self.client_class(), self.hodim)
        for url in (f"{BASE}/renters/", f"{URL}export-excel/", f"{BASE}/contract-files/?contract={self.own.id}"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403)

    def test_non_billing_role_sees_masked_renter(self):
        client = auth(self.client_class(), self.hodim)
        for url in (URL, f"{URL}{self.own.id}/"):
            with self.subTest(url=url):
                text = self._text(client.get(url))
                self.assertIn("Test Renter", text)
                self.assertNotIn(OWN_PINFL, text)
                self.assertNotIn(PHONE, text)
                self.assertNotIn("Andijon", text)

    def test_billing_super_and_rahbariyat_see_full_renter(self):
        for user in (self.super, self.rahbariyat):
            with self.subTest(role=user.role):
                text = self._text(auth(self.client_class(), user).get(f"{URL}{self.own.id}/"))
                self.assertIn(OWN_PINFL, text)
                self.assertIn(PHONE, text)

    def test_scoped_billing_user_cannot_attach_out_of_scope_renter(self):
        resp = self.as_user().post(f"{URL}{self.own.id}/change-renter/",
                                   {"renter": str(self.foreign.renter_id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Contract.objects.get(id=self.own.id).renter_id, self.own.renter_id)
