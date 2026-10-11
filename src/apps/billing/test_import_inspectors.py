"""
Eski billing (billing-urmon.uz) inspektorlarini stat'ga ko'chirish:
    python manage.py import_billing_inspectors --file inspektorlar.json
"""
import json
import tempfile
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.test import TestCase

from apps.billing.models import BillingUserAccess, Region, Xojalik

User = get_user_model()


class ImportInspectorsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = Region.objects.create(name="Андижон вилояти", code="1703", billing_id=3)
        cls.x1 = Xojalik.objects.create(name="Андижон ДЎХ", region=cls.region, inn="300000001")
        cls.x2 = Xojalik.objects.create(name="Шаҳрихон ДЎХ", region=cls.region)
        cls.hash1 = make_password("Inspektor123!")
        cls.hash2 = make_password("Parol456!")

    def _records(self):
        return [
            {   # email bor, departments bo'yicha 2 ta xo'jalik
                "id": 10, "username": "andijon_insp", "email": "insp1@example.uz",
                "first_name": "Akmal", "sur_name": "Karimov", "mid_name": "Baxtiyorovich",
                "phone": "+998901112233", "status": 2, "password": self.hash1,
                "departments": [{"id": 1, "name": "Андижон ДЎХ", "inn": None}, {"id": 2, "name": "Shahrixon DUX", "inn": None}],
                "xojaliklar": [{"id": 5, "name": "Shahrixon DUX", "department": "Шаҳрихон ДЎХ"}],
            },
            {   # email yo'q → username@domen; INN bo'yicha topiladi; biri topilmaydi
                "id": 11, "username": "insp2", "email": "",
                "first_name": "Dilnoza", "sur_name": "Saidova", "mid_name": "",
                "phone": "", "status": 1, "password": self.hash2,
                "departments": [{"id": 3, "name": "Noma'lum xo'jalik", "inn": "300000001"}, {"id": 4, "name": "Yo'q DUX", "inn": None}],
                "xojaliklar": [],
            },
            {   # o'chirilgan (status 3) — o'tkazib yuboriladi
                "id": 12, "username": "old", "email": "old@example.uz",
                "first_name": "Old", "sur_name": "User", "mid_name": "", "phone": "", "status": 3,
                "password": self.hash2, "departments": [], "xojaliklar": [],
            },
        ]

    def _run(self, records=None, **opts):
        path = tempfile.mktemp(suffix=".json")
        with open(path, "w") as f:
            json.dump(records if records is not None else self._records(), f, ensure_ascii=False)
        out = StringIO()
        call_command("import_billing_inspectors", file=path, stdout=out, **opts)
        return out.getvalue()

    def test_creates_billing_users_with_same_password_and_xojaliklar(self):
        out = self._run()
        u1 = User.objects.get(email="insp1@example.uz")
        self.assertEqual(u1.role, "billing_user")
        self.assertEqual((u1.first_name, u1.last_name, u1.father_name), ("Akmal", "Karimov", "Baxtiyorovich"))
        self.assertEqual(u1.username, "andijon_insp")
        self.assertTrue(u1.check_password("Inspektor123!"))
        self.assertEqual(set(u1.billing_access.xojaliklar.values_list("name", flat=True)), {"Андижон ДЎХ", "Шаҳрихон ДЎХ"})

        u2 = User.objects.get(email="insp2@billing-urmon.uz")
        self.assertTrue(u2.check_password("Parol456!"))
        self.assertEqual(list(u2.billing_access.xojaliklar.values_list("name", flat=True)), ["Андижон ДЎХ"])
        self.assertIn("Yo'q DUX", out)  # topilmagan xo'jalik hisobotda

        self.assertFalse(User.objects.filter(email="old@example.uz").exists())
        self.assertIn("yaratildi: 2", out)
        self.assertIn("andijon_insp -> insp1@example.uz", out)

    def test_rerun_is_idempotent_and_update_refreshes_password(self):
        self._run()
        u1 = User.objects.get(email="insp1@example.uz")
        new_hash = make_password("Yangi789!")
        records = self._records()
        records[0]["password"] = new_hash
        out = self._run(records)
        self.assertIn("mavjud: 2", out)
        u1.refresh_from_db()
        self.assertTrue(u1.check_password("Inspektor123!"))  # update'siz o'zgarmaydi
        self._run(records, update=True)
        u1.refresh_from_db()
        self.assertTrue(u1.check_password("Yangi789!"))
        self.assertEqual(User.objects.filter(role="billing_user").count(), 2)

    def test_dry_run_creates_nothing(self):
        out = self._run(dry_run=True)
        self.assertEqual(User.objects.filter(role="billing_user").count(), 0)
        self.assertIn("DRY RUN", out)

    def test_existing_non_billing_email_is_skipped(self):
        User.objects.create_user(email="insp1@example.uz", password="x", first_name="A", last_name="B", role="tashkilot_hodimi")
        out = self._run()
        self.assertIn("o'tkazib yuborildi", out)
        self.assertEqual(User.objects.get(email="insp1@example.uz").role, "tashkilot_hodimi")
        self.assertEqual(BillingUserAccess.objects.count(), 1)
