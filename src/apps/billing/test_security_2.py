"""
Chuqur xavfsizlik auditi (2026-10-27) — billing: ochiq geo-list erkin matn bilan
keshlanmaydi (L4/P1), boshqa xo'jalik ijarachisi pasportsiz biriktirilmaydi (B2),
MIB loglaridagi PII maskalanadi va purge'da o'chiriladi (M1/F5), import xatosi
ichki matnni qaytarmaydi (B3), shartnoma raqami takrorida raqam aks-sado bermaydi (B4).
"""
import uuid
from datetime import timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_reference, make_user
from apps.billing.models import Contract, MibPushLog, Renter
from apps.billing.services import mib_push
from apps.billing.services.contract_writer import _claims_renter
from apps.billing.services.excel_import import import_rows

PUBLIC = f"{BASE}/public"


class GeoListCacheTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        writer = auth(self.client_class(), make_user("super", "billing_super"))
        writer.post(f"{BASE}/contracts/", contract_payload(self.ref, contract_number="PUB-1"), format="json")
        cache.clear()

    def _geo_keys(self):
        return [k for k in cache.keys("billing:public:geo_list:*")]

    def test_number_search_is_not_cached_but_still_works(self):
        for i in range(5):
            resp = self.client.get(f"{PUBLIC}/geo-list/", {"number": f"PUB-{uuid.uuid4()}"[:30]})
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._geo_keys(), [])
        self.assertEqual(self.client.get(f"{PUBLIC}/geo-list/", {"number": "pub-1"}).data["count"], 1)
        self.client.get(f"{PUBLIC}/geo-list/")
        self.assertEqual(len(self._geo_keys()), 1)


class ClaimRenterTest(APITestCase):
    def test_passport_required_when_renter_has_one(self):
        renter = Renter(full_name="Ali Valiyev", pinfl="12345678901234", passport="AA 1234567")
        self.assertFalse(_claims_renter(renter, {"pinfl": "12345678901234", "full_name": "Ali Valiyev"}))
        self.assertFalse(_claims_renter(renter, {"full_name": "Ali Valiyev", "passport": "AB1234567"}))
        self.assertTrue(_claims_renter(renter, {"full_name": "boshqa", "passport": "aa1234567"}))

    def test_name_is_enough_only_without_passport_on_file(self):
        renter = Renter(full_name="Ali Valiyev", pinfl="12345678901234", passport="")
        self.assertTrue(_claims_renter(renter, {"full_name": "ali valiyev"}))
        self.assertFalse(_claims_renter(renter, {"full_name": "boshqa"}))


class MibLogRetentionTest(APITestCase):
    def _log(self, age_days, status=MibPushLog.Status.SENT):
        log = MibPushLog.objects.create(
            contract=None, contract_number=f"C-{age_days}", payload={
                "contract_number": f"C-{age_days}", "rent_user_passport": "AA1234567",
                "rent_user_inn": "12345678901234", "rent_user_phone": "+998901112233",
                "rent_user_address": "Toshkent", "rent_user_full_name": "Ali Valiyev", "rent_area": "1",
            }, payload_hash="x" * 64, dtl=timezone.localdate(), status=status,
        )
        MibPushLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=age_days))
        return log

    def test_old_sent_logs_are_redacted_recent_and_pending_kept(self):
        old = self._log(120)
        recent = self._log(10)
        pending_old = self._log(200, status=MibPushLog.Status.PENDING)
        self.assertEqual(mib_push.redact_old_payloads(days=90), 1)
        old.refresh_from_db(); recent.refresh_from_db(); pending_old.refresh_from_db()
        self.assertEqual(old.payload["rent_user_passport"], "***")
        self.assertEqual(old.payload["rent_user_inn"], "***")
        self.assertEqual(old.payload["contract_number"], "C-120")
        self.assertIn("redacted_at", old.payload)
        self.assertEqual(recent.payload["rent_user_passport"], "AA1234567")
        self.assertEqual(pending_old.payload["rent_user_passport"], "AA1234567")
        # Ikkinchi marta — allaqachon maskalanganlar qayta ishlanmaydi
        self.assertEqual(mib_push.redact_old_payloads(days=90), 0)

    def test_purge_deletes_mib_logs_of_purged_contracts(self):
        ref = make_reference()
        writer = auth(self.client_class(), make_user("super", "billing_super"))
        resp = writer.post(f"{BASE}/contracts/", contract_payload(ref, contract_number="P-1"), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        contract = Contract.objects.get(pk=resp.data["id"])
        MibPushLog.objects.create(contract=contract, contract_number="P-1", payload={"rent_user_passport": "AA1"},
                                  payload_hash="y" * 64, dtl=timezone.localdate(), status=MibPushLog.Status.SENT)
        call_command("purge_billing_contracts", "--confirm-count", str(Contract.objects.count()), stdout=StringIO())
        self.assertEqual(Contract.objects.count(), 0)
        self.assertEqual(MibPushLog.objects.count(), 0)


class ErrorMessageTest(APITestCase):
    def test_import_row_internal_error_is_generic(self):
        user = make_user("super", "billing_super")
        result = import_rows([{"contract": None}], user)
        err = result["errors"]["0"]
        text = str(err)
        self.assertNotIn("Traceback", text)
        self.assertNotIn("NoneType", text)

    def test_duplicate_contract_number_does_not_echo_number(self):
        ref = make_reference()
        writer = auth(self.client_class(), make_user("super", "billing_super"))
        writer.post(f"{BASE}/contracts/", contract_payload(ref, contract_number="UNIQ-77"), format="json")
        resp = writer.post(f"{BASE}/contracts/", contract_payload(ref, contract_number="UNIQ-77", pinfl="22222222222222"),
                           format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("allaqachon mavjud", resp.content.decode())
        self.assertNotIn("UNIQ-77 -", resp.content.decode())
