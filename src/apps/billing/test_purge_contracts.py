"""
purge_billing_contracts: barcha (yoki faqat eski billing'dan import qilingan)
shartnomalarni bog'liq ma'lumotlari va diskdagi fayllari bilan o'chiradi.
Ma'lumotnomalar, GIS konturlar va inspektorlar tegilmaydi.
"""
import io
import os
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.billing._tests_common import BASE, auth, contract_payload, make_billing_user, make_reference, make_user
from apps.billing.models import (
    BillingUserAccess, Bolim, Contract, ContractActivity, ContractFile, ContractHistory, ContractYearlyAmount,
    Region, Renter, Xojalik, XojalikLocation,
)

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class PurgeBillingContractsTest(APITestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.ref = make_reference()
        self.super = make_user("bsuper", "billing_super")
        self.inspector = make_billing_user("inspektor", self.ref.xojalik)
        XojalikLocation.objects.create(name="L", region=self.ref.region, xojalik=self.ref.xojalik,
                                       latitude=40, longitude=72, area_ga=1, parcel_count=1)

        # 2 ta "import qilingan" (legacy tarix + legacy fayl), 1 ta stat'da yaratilgan
        self.imported = [self._create("IMP-1", "11111111111111"), self._create("IMP-2", "22222222222222")]
        for c in self.imported:
            ContractHistory.objects.create(contract=c, reason=ContractHistory.Reason.CREATED,
                                           data={"legacy_reason": "yaratildi", "legacy": {}})
            f = ContractFile(contract=c, uploaded_by=self.super)
            f.file.save(f"documents/billing/contracts/legacy/{c.contract_number}.pdf", ContentFile(PDF), save=False)
            f.save()
        self.native = self._create("STAT-1", "33333333333333")
        native_file = ContractFile(contract=self.native, uploaded_by=self.super)
        native_file.file.save("stat.pdf", ContentFile(PDF), save=False)
        native_file.save()
        self.native_file_path = native_file.file.path
        self.legacy_paths = [f.file.path for f in ContractFile.objects.filter(contract__in=self.imported)]

    def _create(self, number, pinfl):
        payload = contract_payload(self.ref, pinfl=pinfl, contract_number=number)
        resp = auth(self.client_class(), self.super).post(f"{BASE}/contracts/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        return Contract.objects.get(id=resp.data["id"])

    def _run(self, *args):
        out = io.StringIO()
        # Fayllar va kesh commit'dan keyin (on_commit) o'chiriladi — testda commit bo'lmaydi
        with self.captureOnCommitCallbacks(execute=True):
            call_command("purge_billing_contracts", *args, stdout=out)
        return out.getvalue()

    def _reference_untouched(self):
        self.assertTrue(Region.objects.filter(id=self.ref.region.id).exists())
        self.assertTrue(Xojalik.objects.filter(id=self.ref.xojalik.id).exists())
        self.assertTrue(Bolim.objects.filter(id=self.ref.bolim.id).exists())
        self.assertEqual(XojalikLocation.objects.count(), 1)
        self.assertEqual(list(BillingUserAccess.objects.get(user=self.inspector).xojaliklar.all()), [self.ref.xojalik])

    def test_default_is_dry_run_and_deletes_nothing(self):
        out = self._run()
        self.assertIn("DRY-RUN", out)
        self.assertIn("Shartnomalar: 3", out)
        self.assertEqual(Contract.objects.count(), 3)
        self.assertTrue(all(os.path.exists(p) for p in self.legacy_paths))

    def test_wrong_confirm_count_aborts(self):
        with self.assertRaises(CommandError):
            self._run("--confirm-count", "999")
        self.assertEqual(Contract.objects.count(), 3)

    def test_full_purge_removes_contracts_children_renters_and_files(self):
        self._run("--confirm-count", "3")
        self.assertEqual(Contract.objects.count(), 0)
        self.assertEqual(ContractYearlyAmount.objects.count(), 0)
        self.assertEqual(ContractActivity.objects.count(), 0)
        self.assertEqual(ContractFile.objects.count(), 0)
        self.assertEqual(ContractHistory.objects.count(), 0)
        self.assertEqual(Renter.objects.count(), 0)
        self.assertFalse(any(os.path.exists(p) for p in self.legacy_paths + [self.native_file_path]))
        self._reference_untouched()

    def test_only_imported_keeps_stat_contracts(self):
        self._run("--only-imported", "--confirm-count", "2")
        self.assertEqual(list(Contract.objects.values_list("contract_number", flat=True)), ["STAT-1"])
        self.assertEqual(Renter.objects.count(), 1)
        self.assertFalse(any(os.path.exists(p) for p in self.legacy_paths))
        self.assertTrue(os.path.exists(self.native_file_path))
        self._reference_untouched()

    def test_renter_shared_with_remaining_contract_is_kept(self):
        self.native.renter = self.imported[0].renter
        self.native.save(update_fields=["renter"])
        self._run("--only-imported", "--confirm-count", "2")
        self.assertTrue(Renter.objects.filter(id=self.imported[0].renter_id).exists())
