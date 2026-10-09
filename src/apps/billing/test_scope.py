"""
2-bosqich: billing_user doirasi (xo'jaliklar), billing_super, ijara tushumi
statistikasi (ochiq va doiraviy), stat kadastr bo'limi cheklovlari, billing adminkasi.
"""
import io

from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.billing._tests_common import (
    BASE,
    auth,
    contract_payload,
    make_billing_user,
    make_reference,
    make_user,
    square,
)
from apps.billing.models import BillingUser, BillingUserAccess, Bolim, Contract, ContractFile, XojalikLocation
from apps.billing.scope import NOT_ASSIGNED_MESSAGE
from apps.general.models import Organization
from apps.general.permissions import scope_by_organization
from apps.reports.models import Deadline, Report, Statement
from apps.reports.permissions.report_scope import scope_reports_for_user
from apps.users.models import CustomUser

URL = f"{BASE}/contracts/"


def _items(data):
    return data["results"] if isinstance(data, dict) and "results" in data else data


def make_location(ref, lon, lat, size=1.0):
    return XojalikLocation.objects.create(
        name=ref.xojalik.name, region=ref.region, xojalik=ref.xojalik, latitude=lat, longitude=lon,
        bounds=[[lat, lon], [lat + size, lon + size]],
        boundary_geojson={"type": "Feature", "geometry": square(lon, lat, size), "properties": {}},
        area_ga=100, parcel_count=1,
    )


class BillingScopeTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.other = make_reference(code="11:11:11", inn="987654321", name="Boshqa DÒX")
        self.super = make_user("bsuper", "billing_super")
        self.user = make_billing_user("billing", self.ref.xojalik)
        self.own = self._create(self.super, self.ref, pinfl="11111111111111", contract_number="OWN-1")
        self.foreign = self._create(
            self.super, self.other, pinfl="22222222222222", contract_number="FOR-1",
            rent_area="7.50", yearly=[{"year": 2025, "contract_amount": "300", "calculated_amount": "300",
                                       "paid_amount": "100", "penalty_amount": "0"}],
        )

    def _create(self, user, ref, *, yearly=None, **overrides):
        payload = contract_payload(ref, **overrides)
        if yearly is not None:
            payload["yearly_amounts"] = yearly
        resp = auth(self.client_class(), user).post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        return Contract.objects.get(id=resp.data["id"])

    def as_user(self):
        return auth(self.client_class(), self.user)


class BillingUserScopeTest(BillingScopeTestBase):
    def test_list_and_detail_are_scoped(self):
        client = self.as_user()
        ids = [row["id"] for row in client.get(URL).data["results"]]
        self.assertEqual(ids, [str(self.own.id)])
        self.assertEqual(client.get(f"{URL}{self.own.id}/").status_code, 200)
        for suffix in ("", "history/"):
            self.assertEqual(client.get(f"{URL}{self.foreign.id}/{suffix}").status_code, 404)
        self.assertEqual(client.patch(f"{URL}{self.foreign.id}/", {"contract": {"rent_area": "1"}}, format="json").status_code, 404)
        self.assertEqual(client.post(f"{URL}{self.foreign.id}/status/", {"status": "inactive", "cancel_reason": "x"}, format="json").status_code, 404)

    def test_summary_counts_geo_list_are_scoped(self):
        client = self.as_user()
        self.assertEqual(client.get(f"{URL}summary/").data["total_count"], 1)
        self.assertEqual(client.get(f"{URL}counts/").data["all"], 1)
        geo = client.get(f"{URL}geo-list/").data
        self.assertEqual([str(r["id"]) for r in geo["results"]], [str(self.own.id)])
        self.assertEqual(client.get(f"{URL}export-excel/").status_code, 200)

    def test_create_outside_scope_is_rejected(self):
        resp = self.as_user().post(URL, contract_payload(self.other, pinfl="33333333333333", contract_number="X-1"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data, {"errors": {"contract": {"xojalik": NOT_ASSIGNED_MESSAGE}}})
        self.assertEqual(Contract.objects.count(), 2)

    def test_create_inside_scope_and_patch_to_foreign_xojalik(self):
        client = self.as_user()
        resp = client.post(URL, contract_payload(self.ref, pinfl="44444444444444", contract_number="IN-2"), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        resp = client.patch(f"{URL}{self.own.id}/", {"contract": {"xojalik": str(self.other.xojalik.id)}}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["errors"]["contract"]["xojalik"], NOT_ASSIGNED_MESSAGE)
        self.own.refresh_from_db()
        self.assertEqual(self.own.xojalik_id, self.ref.xojalik.id)

    def test_cannot_edit_foreign_renter_by_id(self):
        resp = self.as_user().patch(
            f"{URL}{self.own.id}/", {"renter": {"id": str(self.foreign.renter_id), "full_name": "Hack"}}, format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id", resp.data["errors"]["renter"])

    def test_import_outside_scope_row_error(self):
        rows = [
            {"contract": {"contract_date": "01.02.2026", "xojalik_inn": self.ref.xojalik.inn, "rent_area": "3", "bolim": "Yangi bo'lim A"},
             "renter": {"pinfl": "55555555555555", "full_name": "Ichki"}},
            {"contract": {"contract_date": "01.02.2026", "xojalik_inn": self.other.xojalik.inn, "rent_area": "3", "bolim": "Yangi bo'lim B"},
             "renter": {"pinfl": "66666666666666", "full_name": "Tashqi"}},
        ]
        resp = self.as_user().post(f"{URL}import-excel/", {"rows": rows}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["saved"], [0])
        self.assertEqual(resp.data["errors"]["1"], {"contract": {"xojalik": NOT_ASSIGNED_MESSAGE}})
        # doiradan tashqari xo'jalikda bo'lim yaratilmadi
        self.assertFalse(Bolim.objects.filter(name="Yangi bo'lim B").exists())
        self.assertTrue(Bolim.objects.filter(name="Yangi bo'lim A", xojalik=self.ref.xojalik).exists())

    def test_reference_lists_are_scoped(self):
        client = self.as_user()
        self.assertEqual([str(r["id"]) for r in client.get(f"{BASE}/xojaliklar/").data], [str(self.ref.xojalik.id)])
        self.assertEqual({str(r["xojalik"]) for r in client.get(f"{BASE}/bolimlar/").data}, {str(self.ref.xojalik.id)})
        renters = client.get(f"{BASE}/renters/").data["results"]
        self.assertEqual([str(r["id"]) for r in renters], [str(self.own.renter_id)])
        self.assertEqual(renters[0]["contracts_count"], 1)

    def test_locations_and_konturs_are_scoped(self):
        own_loc = make_location(self.ref, 72.0, 40.0)
        foreign_loc = make_location(self.other, 60.0, 40.0)
        client = self.as_user()
        self.assertEqual([str(r["id"]) for r in client.get(f"{BASE}/xojalik-locations/").data], [str(own_loc.id)])
        self.assertEqual(client.get(f"{BASE}/xojalik-locations/{foreign_loc.id}/").status_code, 404)
        self.assertEqual(client.get(f"{BASE}/xojalik-locations/{own_loc.id}/").status_code, 200)

    def test_files_are_scoped(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = self.as_user()
        pdf = SimpleUploadedFile("a.pdf", b"%PDF-1.4\n%test\n", content_type="application/pdf")
        resp = client.post(f"{BASE}/contract-files/", {"contract": str(self.foreign.id), "file": pdf}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ContractFile.objects.count(), 0)
        pdf = SimpleUploadedFile("b.pdf", b"%PDF-1.4\n%test\n", content_type="application/pdf")
        resp = client.post(f"{BASE}/contract-files/", {"contract": str(self.own.id), "file": pdf}, format="multipart")
        self.assertEqual(resp.status_code, 201, resp.data)
        foreign_file = ContractFile.objects.create(contract=self.foreign, file=SimpleUploadedFile("c.pdf", b"%PDF-1.4\n"))
        self.assertEqual(client.get(f"{BASE}/contract-files/").data["count"], 1)
        self.assertEqual(client.delete(f"{BASE}/contract-files/{foreign_file.id}/").status_code, 404)

    def test_user_without_assignment_sees_nothing(self):
        lonely = make_user("lonely", "billing_user")
        client = auth(self.client_class(), lonely)
        self.assertEqual(client.get(URL).data["count"], 0)
        self.assertEqual(client.get(f"{BASE}/xojaliklar/").data, [])

    def test_billing_super_and_regular_roles_see_all(self):
        for user in (self.super, make_user("reader", "rahbariyat")):
            with self.subTest(role=user.role):
                self.assertEqual(auth(self.client_class(), user).get(URL).data["count"], 2)
                self.assertEqual(len(auth(self.client_class(), user).get(f"{BASE}/xojaliklar/").data), 2)


class RentStatsTest(BillingScopeTestBase):
    EXPECTED_YEARS = [
        {"year": 2025, "total_area": 20.0, "total_calculated": 800.0, "price_per_hectare": 40.0},
        {"year": 2026, "total_area": 12.5, "total_calculated": 600.0, "price_per_hectare": 48.0},
    ]

    def test_public_rent_stats_anonymous(self):
        resp = self.client.get(f"{BASE}/public/rent-stats/", {"from_year": 2020, "to_year": 2026})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["from_year"], 2020)
        self.assertEqual(resp.data["to_year"], 2026)
        self.assertEqual(resp.data["years"], self.EXPECTED_YEARS)
        self.assertEqual(resp.data["average_annual"], 700.0)
        self.assertEqual(resp.data["growth"], {"diff": -200.0, "percent": -25.0})
        self.assertEqual(resp.data["max"], {"year": 2025, "total_calculated": 800.0})
        # shaxsiy ma'lumot yo'q
        body = resp.content.decode()
        for secret in ("11111111111111", "Test Renter", "OWN-1"):
            self.assertNotIn(secret, body)

    def test_public_rent_stats_filters_and_cache(self):
        resp = self.client.get(f"{BASE}/public/rent-stats/", {"from_year": 2026, "to_year": 2026, "xojalik": str(self.ref.xojalik.id)})
        self.assertEqual(resp.data["years"], [self.EXPECTED_YEARS[1]])
        self.assertEqual(resp.data["growth"], {"diff": 0.0, "percent": 0.0})
        self.assertEqual(self.client.get(f"{BASE}/public/rent-stats/", {"xojalik": "bad"}).status_code, 400)
        # 5 daqiqa cache: yangi ma'lumot darhol ko'rinmaydi
        first = self.client.get(f"{BASE}/public/rent-stats/", {"from_year": 2020, "to_year": 2026}).data
        self.foreign.yearly_amounts.update(calculated_amount=0)
        self.assertEqual(self.client.get(f"{BASE}/public/rent-stats/", {"from_year": 2020, "to_year": 2026}).data, first)

    def test_public_xojaliklar(self):
        resp = self.client.get(f"{BASE}/public/xojaliklar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sorted(r["name"] for r in resp.data), sorted([self.ref.xojalik.name, self.other.xojalik.name]))
        self.assertEqual(set(resp.data[0]), {"id", "name"})

    def test_public_endpoints_ignore_bad_token(self):
        resp = self.client.get(f"{BASE}/public/xojaliklar/", HTTP_AUTHORIZATION="Bearer broken")
        self.assertEqual(resp.status_code, 200)

    def test_scoped_rent_stats(self):
        self.assertEqual(self.client.get(f"{URL}rent-stats/").status_code, 401)
        data = self.as_user().get(f"{URL}rent-stats/", {"from_year": 2020, "to_year": 2026}).data
        self.assertEqual(data["years"], [
            {"year": 2025, "total_area": 12.5, "total_calculated": 500.0, "price_per_hectare": 40.0},
            {"year": 2026, "total_area": 12.5, "total_calculated": 600.0, "price_per_hectare": 48.0},
        ])
        data = auth(self.client_class(), self.super).get(f"{URL}rent-stats/", {"from_year": 2020, "to_year": 2026}).data
        self.assertEqual(data["years"], self.EXPECTED_YEARS)


class CreateBillingUserCommandTest(APITestCase):
    def test_role_and_xojaliklar(self):
        ref = make_reference()
        other = make_reference(code="11:11:11", inn="987654321", name="Boshqa DÒX")
        call_command(
            "create_billing_user", "--email", "inspektor@example.com", "--password", "StrongPass123!",
            "--first-name", "I", "--last-name", "N", "--xojalik", ref.xojalik.name, "--xojalik", other.xojalik.inn,
            stdout=io.StringIO(),
        )
        user = CustomUser.objects.get(email="inspektor@example.com")
        self.assertEqual(user.role, "billing_user")
        self.assertEqual(set(user.billing_access.xojaliklar.all()), {ref.xojalik, other.xojalik})
        call_command(
            "create_billing_user", "--email", "super@example.com", "--password", "StrongPass123!",
            "--first-name", "S", "--last-name", "U", "--role", "billing_super", stdout=io.StringIO(),
        )
        self.assertEqual(CustomUser.objects.get(email="super@example.com").role, "billing_super")


class KadastrScopeTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kadastr = Statement.objects.create(name="O‘rmon kadastri, ijara", name_ru="Лесной кадастр, аренда")
        cls.kadastr_form = Statement.objects.create(name="Yer o'zlashtirish", parent=cls.kadastr)
        cls.other = Statement.objects.create(name="Boshqa bo'lim")
        cls.other_form = Statement.objects.create(name="Boshqa shakl", parent=cls.other)
        cls.org_a = Organization.objects.create(name="Tashkilot A", region="tashkent")
        cls.org_b = Organization.objects.create(name="Tashkilot B", region="namangan")
        cls.deadline_k = Deadline.objects.create(statement=cls.kadastr_form, submit_at="2026")
        cls.deadline_o = Deadline.objects.create(statement=cls.other_form, submit_at="2026")

    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.ref.xojalik.organization = self.org_a
        self.ref.xojalik.save()
        self.user = make_billing_user("billing", self.ref.xojalik)
        self.super = make_user("bsuper", "billing_super")
        self.rep_k_a = Report.objects.create(organization=self.org_a, statement=self.kadastr_form, deadline=self.deadline_k)
        self.rep_k_b = Report.objects.create(organization=self.org_b, statement=self.kadastr_form, deadline=self.deadline_k)
        self.rep_o_a = Report.objects.create(organization=self.org_a, statement=self.other_form, deadline=self.deadline_o)

    def test_statement_list_only_kadastr_parent(self):
        for user in (self.user, self.super):
            with self.subTest(role=user.role):
                data = auth(self.client_class(), user).get("/api/v1/reports/statements/").data
                self.assertEqual([str(s["id"]) for s in _items(data)], [str(self.kadastr.id)])
        reader = make_user("reader", "rahbariyat")
        data = auth(self.client_class(), reader).get("/api/v1/reports/statements/").data
        self.assertEqual(len(_items(data)), 2)

    def test_report_scope(self):
        self.assertEqual(set(scope_reports_for_user(Report.objects.all(), self.user)), {self.rep_k_a})
        self.assertEqual(set(scope_reports_for_user(Report.objects.all(), self.super)), {self.rep_k_a, self.rep_k_b})
        self.assertEqual(set(scope_by_organization(Report.objects.all(), self.user)), {self.rep_k_a, self.rep_o_a})
        self.assertEqual(scope_by_organization(Report.objects.all(), self.super).count(), 3)
        lonely = make_user("lonely", "billing_user")
        self.assertFalse(scope_reports_for_user(Report.objects.all(), lonely).exists())

    def test_report_list_endpoint(self):
        resp = auth(self.client_class(), self.user).get("/api/v1/reports/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([str(r["id"]) for r in _items(resp.data)], [str(self.rep_k_a.id)])

    def test_deadlines_and_users(self):
        data = auth(self.client_class(), self.super).get("/api/v1/reports/deadlines/").data
        self.assertEqual([str(d["id"]) for d in _items(data)], [str(self.deadline_k.id)])
        data = auth(self.client_class(), self.user).get("/api/v1/reports/users/").data
        self.assertEqual([u["user_number"] for u in _items(data)], [self.user.user_number])

    def test_statement_checks_on_columns_filtered_and_export(self):
        client = auth(self.client_class(), self.user)
        self.assertEqual(client.get("/api/v1/reports/statement-columns/", {"statement": str(self.other_form.id)}).status_code, 403)
        self.assertEqual(client.get("/api/v1/reports/statement-columns/").status_code, 403)
        self.assertEqual(client.get("/api/v1/reports/statement-columns/", {"statement": str(self.kadastr_form.id)}).status_code, 200)
        self.assertEqual(client.get("/api/v1/reports/filtered-general/", {"statement": str(self.other_form.id), "deadline": str(self.deadline_k.id)}).status_code, 403)
        self.assertNotEqual(client.get("/api/v1/reports/filtered-general/", {"statement": str(self.kadastr_form.id), "deadline": str(self.deadline_k.id)}).status_code, 403)
        resp = client.post("/api/v1/reports/export-excel/", {"report_ids": [str(self.rep_o_a.id)], "mode": "json"}, format="json")
        self.assertEqual(resp.status_code, 403)
        # boshqa tashkilot hisoboti doiradan tashqari -> topilmadi
        resp = client.post("/api/v1/reports/export-excel/", {"report_ids": [str(self.rep_k_b.id)], "mode": "json"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_regular_roles_unaffected(self):
        reader = auth(self.client_class(), make_user("reader", "rahbariyat"))
        self.assertEqual(reader.get("/api/v1/reports/statement-columns/", {"statement": str(self.other_form.id)}).status_code, 200)


class BillingAdminTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.ref = make_reference()
        self.admin = make_user("root", "super_admin", is_superuser=True, is_staff=True)
        self.billing = make_billing_user("billing", self.ref.xojalik)
        self.client.force_login(self.admin)

    def test_pages_load(self):
        for url in ("/billing-admin/", "/billing-admin/billing/billinguser/", "/billing-admin/billing/billinguser/add/",
                    f"/billing-admin/billing/billinguser/{self.billing.id}/change/",
                    f"/billing-admin/billing/billinguser/{self.billing.id}/password/",
                    "/billing-admin/billing/contract/", "/billing-admin/billing/xojalik/"):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, url)
        self.assertContains(self.client.get("/billing-admin/"), "Ijara billing boshqaruvi")
        bare_login = self.client_class().get("/billing-admin/login/")
        self.assertRedirects(bare_login, "/billing-admin/login/?next=%2Fbilling-admin%2F", fetch_redirect_response=False)
        login = self.client_class().get("/billing-admin/login/?next=/billing-admin/")
        self.assertContains(login, "Ijara billing boshqaruvi")
        changelist = self.client.get("/billing-admin/billing/billinguser/")
        self.assertContains(changelist, self.billing.email)
        self.assertNotContains(changelist, f"/billing-admin/billing/billinguser/{self.admin.id}/change/")

    def test_billing_models_not_in_stat_admin(self):
        self.assertEqual(self.client.get("/admin/billing/contract/").status_code, 404)

    def test_create_billing_user_via_admin(self):
        resp = self.client.post("/billing-admin/billing/billinguser/add/", {
            "email": "New.Inspector@example.com", "first_name": "Yangi", "last_name": "Inspektor",
            "password1": "Xk9#mPq2!vLzW", "password2": "Xk9#mPq2!vLzW",
            "role": "billing_user", "xojaliklar": [str(self.ref.xojalik.id)], "organization": "",
            "is_active": "on", "_save": "Save",
        })
        self.assertEqual(resp.status_code, 302, getattr(resp, "context_data", {}).get("adminform") and resp.context_data["adminform"].form.errors)
        user = BillingUser.objects.get(email="new.inspector@example.com")
        self.assertTrue(user.check_password("Xk9#mPq2!vLzW"))
        self.assertNotEqual(user.password, "Xk9#mPq2!vLzW")
        self.assertEqual(user.role, "billing_user")
        self.assertFalse(user.is_staff)
        self.assertEqual(list(BillingUserAccess.objects.get(user=user).xojaliklar.all()), [self.ref.xojalik])
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["billing_user"])

    def test_role_choices_limited(self):
        resp = self.client.post("/billing-admin/billing/billinguser/add/", {
            "email": "x@example.com", "first_name": "X", "last_name": "Y",
            "password1": "Xk9#mPq2!vLzW", "password2": "Xk9#mPq2!vLzW", "role": "super_admin", "is_active": "on",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email="x@example.com").exists())

    def test_stat_admin_hides_billing_users(self):
        resp = self.client.get("/admin/users/customuser/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.billing.email)
        add = self.client.get("/admin/users/customuser/add/")
        self.assertNotContains(add, 'value="billing_user"')
        self.assertNotContains(add, 'value="billing_super"')
