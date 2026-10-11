"""
Eski billing (billing-urmon.uz) shartnomalarini stat'ga ko'chirish:
    python manage.py import_billing_contracts --file contracts.json --media-root <legacy media>
"""
import json
import os
import tempfile
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.billing.models import (
    ActivityType, Bolim, Contract, ContractFile, ContractHistory, District, LandType, PrivilegeType,
    Region, Renter, Xojalik,
)

User = get_user_model()


def _export():
    return {
        "regions": [{"id": 3, "name": "Андижон вилояти", "code": "03", "status": 1},
                    {"id": 9, "name": "Самарқанд вилояти", "code": "09", "status": 1}],
        "districts": [{"id": 31, "region_id": 3, "code": "0301", "name": "Андижон тумани", "status": 1},
                      {"id": 91, "region_id": 9, "code": "0901", "name": "Булунғур тумани", "status": 1}],
        "departments": [{"id": 1, "name": "Андижон КИДЎХ", "inn": "300000001", "code": "23:02", "account_detail": "h/r 1", "region_id": 3, "status": 1},
                        {"id": 2, "name": "Булунғур ДЎХ", "inn": None, "code": None, "account_detail": None, "region_id": 9, "status": 1}],
        "branches": [{"id": 5, "department_id": 1, "name": "1-bo'lim"}],
        "activity_types": [{"id": 1, "name": "Асаларичилик", "description": None, "parent_id": None}],
        "land_types": [{"id": 1, "name": "Ўрмон", "description": None, "parent_id": None},
                       {"id": 2, "name": "Ўрмон билан қопланган", "description": None, "parent_id": 1}],
        "privilege_types": [{"id": 1, "name": "Ёш оила", "description": None, "parent_id": None, "month": 12}],
        "renters": [
            {"id": 100, "username": "u100", "email": "", "first_name": "Dilshodbek", "sur_name": "Yuldashev", "mid_name": "Adhamjon o'g'li",
             "full_name": "Yuldashev Dilshodbek Adhamjon o'g'li", "pinfl": "31234567890123", "stir": "", "passport": "AA1234567",
             "phone": "+998901112233", "per_adr": "Andijon", "tem_adr": None, "citizenship": "O'zbekiston", "birth_place": None,
             "birth_date": None, "is_legal_entity": False, "legal_name": None, "legal_stir": None, "status": 2},
            {"id": 101, "username": "u101", "email": "", "first_name": "", "sur_name": "", "mid_name": "",
             "full_name": None, "pinfl": "", "stir": "", "passport": None, "phone": None, "per_adr": None, "tem_adr": None,
             "citizenship": None, "birth_place": None, "birth_date": None, "is_legal_entity": True, "legal_name": "Yashil MChJ",
             "legal_stir": "305555555", "status": 2},
        ],
        "contracts": [
            {"id": 1, "number": "1235/43", "contract_number": "1235/43", "rented_user_id": 100, "department_id": 1, "branch_id": 5,
             "region_id": 3, "district_id": 31, "contract_date": "2020-03-12", "expired_date": "2069-12-31", "auction_date": None,
             "exemptioned_date": None, "canceled_date": None, "cancel_reason": None, "status": "Faol",
             "rent_amount": "11582266.0000000000", "paid_amount": "11497430.00", "penalty_amount": "0.00", "bhm_amount": None,
             "rent_area": "0.4200000000", "cadastral_number": "03:01:01", "is_entity": False, "circle": "1", "section": "2",
             "counter": "3", "massive": None, "latitude": "40.7812345", "longitude": "72.3456789",
             "boundary_geojson": {"type": "Polygon", "coordinates": [[[72.3, 40.7], [72.4, 40.7], [72.4, 40.8], [72.3, 40.7]]]},
             "created_at": "2020-03-12T10:00:00+05:00", "updated_at": "2025-01-01T10:00:00+05:00",
             "activities": [{"type_id": 1, "area": "0.42"}],
             "lands": [{"type_id": 2, "area": "0.42"}],
             "privileges": [{"type_id": 1, "area": "0.10"}],
             "actions": [{"vacancy": "2.00", "own_investment": "1000.00",
                          "products": [{"product_export": "Asal", "product_amount": "100 kg", "export_amount": "0.00"}]}],
             "yearly": [{"year": 2025, "contract_amount": "5000000.00", "calculated_amount": "5000000.00", "paid_amount": "5000000.00", "penalty_amount": "0.00"},
                        {"year": 2026, "contract_amount": "6582266.00", "calculated_amount": "6582266.00", "paid_amount": "6497430.00", "penalty_amount": "0.00"}],
             "files": [{"id": 7, "file": "contracts/2020/03/shartnoma.pdf", "description": "Asl nusxa", "uploaded_by": "inspektor1", "created_at": "2020-03-12T11:00:00+05:00"},
                       {"id": 8, "file": "contracts/2020/03/yoq.pdf", "description": None, "uploaded_by": None, "created_at": "2020-03-12T11:00:00+05:00"}],
             "history": [{"reason": "Ijarachi o'zgardi", "history": {"old": {"user": "A"}, "new": {"user": "B"}}, "executor": "inspektor1", "created_at": "2021-05-05T09:00:00+05:00"},
                         {"reason": "Shartnoma xolati o'zgardi", "history": {"status": "Faol"}, "executor": None, "created_at": "2022-05-05T09:00:00+05:00"}]},
            {"id": 2, "number": "25", "contract_number": "25", "rented_user_id": 101, "department_id": 2, "branch_id": None,
             "region_id": 9, "district_id": 91, "contract_date": "2020-03-12", "expired_date": "2029-12-31", "auction_date": None,
             "exemptioned_date": None, "canceled_date": "2024-01-01", "cancel_reason": "Muddati", "status": "Faol emas",
             "rent_amount": "1255000.00", "paid_amount": "1250000.00", "penalty_amount": "0.00", "bhm_amount": None,
             "rent_area": "0.05", "cadastral_number": None, "is_entity": True, "circle": None, "section": None,
             "counter": None, "massive": None, "latitude": None, "longitude": None, "boundary_geojson": None,
             "created_at": "2020-03-12T10:00:00+05:00", "updated_at": "2024-01-01T10:00:00+05:00",
             "activities": [], "lands": [], "privileges": [], "actions": [], "yearly": [], "files": [], "history": []},
        ],
    }


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ImportContractsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.r_andijon = Region.objects.create(name="Андижон вилояти", code="1703", billing_id=3)
        cls.r_samarqand = Region.objects.create(name="Самарқанд вилояти", code="1718", billing_id=9)
        cls.xojalik = Xojalik.objects.create(name="Андижон ДЎХ", region=cls.r_andijon)
        ActivityType.objects.create(name="Асаларичилик")
        cls.inspektor = User.objects.create_user(
            email="insp1@example.uz", password="x", first_name="I", last_name="N", role="billing_user", username="inspektor1",
        )
        cls.media = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.media, "contracts/2020/03"))
        with open(os.path.join(cls.media, "contracts/2020/03/shartnoma.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 test")

    def _run(self, data=None, **opts):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w") as f:
            json.dump(data if data is not None else _export(), f, ensure_ascii=False)
        out = StringIO()
        call_command("import_billing_contracts", file=path, media_root=self.media, stdout=out, **opts)
        return out.getvalue()

    def test_imports_contracts_with_all_sections(self):
        out = self._run()
        self.assertEqual(Contract.objects.count(), 2)
        c = Contract.objects.get(number="1235/43")
        self.assertEqual(c.xojalik, self.xojalik)                      # "Андижон КИДЎХ" -> "Андижон ДЎХ"
        self.assertEqual(c.bolim.name, "1-bo'lim")
        self.assertEqual((c.region, c.district.name), (self.r_andijon, "Андижон тумани"))
        self.assertEqual(c.status, Contract.Status.ACTIVE)
        self.assertEqual(str(c.rent_amount), "11582266.00")
        self.assertEqual(str(c.rent_area), "0.42")
        self.assertEqual(c.renter.pinfl, "31234567890123")
        self.assertEqual(c.renter.full_name, "Yuldashev Dilshodbek Adhamjon o'g'li")
        self.assertEqual(c.boundary_geojson["type"], "Polygon")
        self.assertEqual(str(c.latitude), "40.7812345")
        self.assertEqual(c.created_at.isoformat(), "2020-03-12T05:00:00+00:00")
        self.assertEqual([a.type.name for a in c.activities.all()], ["Асаларичилик"])
        self.assertEqual([(l.type.name, l.type.parent.name) for l in c.lands.all()], [("Ўрмон билан қопланган", "Ўрмон")])
        self.assertEqual([p.type.month for p in c.privileges.all()], [12])
        self.assertEqual(c.actions.get().products.get().product_export, "Asal")
        self.assertEqual(list(c.yearly_amounts.values_list("year", flat=True)), [2025, 2026])
        # fayllar: bor fayl ko'chadi, yo'q fayl hisobotda
        f = c.files.get()
        self.assertEqual(f.file.name, "documents/billing/contracts/legacy/contracts/2020/03/shartnoma.pdf")
        self.assertEqual(f.uploaded_by, self.inspektor)
        self.assertTrue(os.path.exists(f.file.path))
        self.assertIn("yoq.pdf", out)
        # tarix
        reasons = list(c.history.order_by("created_at").values_list("reason", flat=True))
        self.assertEqual(reasons, [ContractHistory.Reason.RENTER_CHANGED, ContractHistory.Reason.STATUS_CHANGED])
        h = c.history.order_by("created_at").first()
        self.assertEqual(h.executor, self.inspektor)
        self.assertEqual(h.data["legacy_reason"], "Ijarachi o'zgardi")
        self.assertEqual(h.created_at.isoformat(), "2021-05-05T04:00:00+00:00")

        c2 = Contract.objects.get(number="25")
        self.assertEqual(c2.status, Contract.Status.INACTIVE)
        self.assertEqual(c2.xojalik.name, "Булунғур ДЎХ")               # yo'q xo'jalik yaratiladi
        self.assertEqual(c2.xojalik.region, self.r_samarqand)
        self.assertEqual(c2.renter.stir, "305555555")
        self.assertEqual(c2.renter.full_name, "Yashil MChJ")
        self.assertTrue(c2.renter.is_legal_entity)
        self.assertIn("Булунғур ДЎХ", out)
        self.assertIn("shartnomalar: yaratildi 2", out)

    def test_rerun_updates_without_duplicates(self):
        self._run()
        data = _export()
        data["contracts"][0]["paid_amount"] = "11582266.00"
        data["contracts"][0]["status"] = "Faol emas"
        out = self._run(data)
        self.assertEqual(Contract.objects.count(), 2)
        self.assertEqual(Renter.objects.count(), 2)
        self.assertEqual(Xojalik.objects.count(), 2)
        self.assertEqual(Bolim.objects.count(), 1)
        self.assertEqual(District.objects.count(), 2)
        c = Contract.objects.get(number="1235/43")
        self.assertEqual(c.status, Contract.Status.INACTIVE)
        self.assertEqual(c.files.count(), 1)
        self.assertEqual(c.history.count(), 2)
        self.assertEqual(c.yearly_amounts.count(), 2)
        self.assertEqual(ContractFile.objects.count(), 1)
        self.assertIn("yangilandi 2", out)

    def test_dry_run_writes_nothing(self):
        out = self._run(dry_run=True)
        self.assertEqual(Contract.objects.count(), 0)
        self.assertEqual(Renter.objects.count(), 0)
        self.assertFalse(os.path.exists(os.path.join(settings.MEDIA_ROOT, "documents/billing/contracts/legacy")))
        self.assertIn("DRY RUN", out)

    def test_renters_deduplicated_by_pinfl(self):
        data = _export()
        data["renters"].append({**data["renters"][0], "id": 102, "username": "u102", "full_name": "Yuldashev D."})
        data["contracts"][1]["rented_user_id"] = 102
        self._run(data)
        # 100 va 102 bitta ijarachi (JSHSHIR bir xil), 101 alohida (yuridik shaxs, INN)
        self.assertEqual(Renter.objects.count(), 2)
        self.assertEqual(Contract.objects.get(number="25").renter, Contract.objects.get(number="1235/43").renter)
        self.assertEqual(Contract.objects.get(number="25").renter.pinfl, "31234567890123")
