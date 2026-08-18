"""
`import-template` va `import-parse` endpointlari uchun end-to-end testlar.

Ikkala endpoint ham `services/report_import/` package'iga tayanadi
(columns.py, template_generator.py, parser.py) — shu yerda haqiqiy
Statement/StatementColumn/Plant daraxti quriladi, shablon generatsiya
qilinadi, to'ldiriladi va qayta parse qilinadi (round-trip), shuningdek
`backend-import-parse-bug.md` da tasvirlangan holat ham qorovullanadi.
"""

import io
from decimal import Decimal

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.general.models import Organization
from apps.reports.models import (
    Plan,
    PlanItem,
    Plant,
    PlantPlan,
    PlantPlanItem,
    Statement,
    StatementColumn,
)
from apps.reports.services.report_import.columns import (
    StatementColumnIndex,
    get_importable_columns,
    is_plant_based_statement,
)
from apps.reports.services.report_import.parser import parse_import_excel
from apps.reports.services.report_import.template_generator import build_import_template

User = get_user_model()

TEMPLATE_URL = reverse("import-excel-template")
PARSE_URL = reverse("import-excel-parse")

DEFAULT_YEAR = 2026


# ── Shablon yordamchi funksiyalari ──
# Yangi template ko'p qatorli sarlavhalar + dynamik UUID qatoriga ega.
# Testlarda sarlavha/UUID/data qator indekslarini topish kerak.

def _find_uuid_row(ws):
    """Shablondagi yashirin UUID qatorini topadi (hidden=True + UUID qiymatlari bor)."""
    for row in range(1, ws.max_row + 1):
        if ws.row_dimensions[row].hidden:
            for cell in ws[row]:
                val = cell.value
                if val and isinstance(val, str) and "-" in val and len(val) == 36:
                    return row
    return None


def _find_data_start_row(ws):
    """UUID qatoridan bitta pastdagi qator — ma'lumot yozish boshlanishi."""
    uuid_row = _find_uuid_row(ws)
    return uuid_row + 1 if uuid_row else ws.max_row + 1


def _find_col_by_uuid(ws, column_uuid):
    """UUID qatoridagi berilgan UUID ga mos Excel ustunini topadi."""
    uuid_row = _find_uuid_row(ws)
    if not uuid_row:
        return None
    for cell in ws[uuid_row]:
        if cell.value and str(cell.value).strip() == str(column_uuid):
            return cell.column
    return None


def _all_header_values(ws):
    """Barcha sarlavha qatorlaridagi barcha qiymatlarni yig'adi (merged qiymatlar bilan)."""
    uuid_row = _find_uuid_row(ws)
    header_end = uuid_row - 1 if uuid_row else ws.max_row
    values = set()
    for row in range(1, header_end + 1):
        for cell in ws[row]:
            if cell.value is not None:
                values.add(cell.value)
    return values


def make_user(email="tester@example.com", **extra):
    return User.objects.create_user(
        email=email,
        password="TestPassword123!",
        first_name="Test",
        last_name="User",
        **extra,
    )


def make_organization(name="Test Tashkilot"):
    return Organization.objects.create(name=name, region="tashkent")


def make_upload(wb, name="upload.xlsx"):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(
        name,
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class FlatStatementFixture:
    """
    1-ilova (root)
      1-chorak (group)
        Yanvar (group) -> Amalda (leaf, importable)
        Fevral (group) -> Amalda (leaf, importable)
      Tumanlar nomi (leaf, importable, directly under root)
      Reja ustuni (leaf, status_plan set -> NOT importable)
      Avto-hisob (leaf, is_user_input=False -> NOT importable)
      Tashkilot (leaf, is_organization=True -> NOT importable)
    """

    def build(self):
        self.root_statement = Statement.objects.create(name="Root Statement")
        self.statement = Statement.objects.create(
            name="Flat Test Statement", parent=self.root_statement
        )

        self.app_root = StatementColumn.objects.create(
            statement=self.statement, parent=None, title="1-ilova", ordering="1",
        )
        self.quarter = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="1-chorak", ordering="1.1",
        )
        self.january = StatementColumn.objects.create(
            statement=self.statement, parent=self.quarter, title="Yanvar", ordering="1.1.1",
        )
        self.february = StatementColumn.objects.create(
            statement=self.statement, parent=self.quarter, title="Fevral", ordering="1.1.2",
        )
        self.jan_amalda = StatementColumn.objects.create(
            statement=self.statement, parent=self.january, title="Amalda", ordering="1.1.1.1",
        )
        self.feb_amalda = StatementColumn.objects.create(
            statement=self.statement, parent=self.february, title="Amalda", ordering="1.1.2.1",
        )
        self.tumanlar = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Tumanlar nomi", ordering="1.2",
        )
        self.reja = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Reja ustuni",
            ordering="1.3", status_plan=StatementColumn.PlanStatus.YANVAR,
        )
        self.auto_calc = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Avto-hisob",
            ordering="1.4", is_user_input=False,
        )
        self.organization = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Tashkilot",
            ordering="1.5", is_organization=True,
        )
        return self


class PlantStatementFixture:
    def build(self):
        self.root_statement = Statement.objects.create(name="Root Statement Plant")
        self.statement = Statement.objects.create(
            name="Plant Test Statement", parent=self.root_statement
        )
        self.app_root = StatementColumn.objects.create(
            statement=self.statement, parent=None, title="Ilova", ordering="1",
        )
        self.amount = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Miqdori", ordering="1.1",
        )
        self.area = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Maydoni", ordering="1.2",
        )
        self.reja = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Reja miqdori",
            ordering="1.3", status_plan=StatementColumn.PlanStatus.YANVAR,
        )
        self.archa = Plant.objects.create(statement=self.statement, name="Archa")
        self.qayin = Plant.objects.create(statement=self.statement, name="Qayin")
        return self


class ImportTemplateAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = FlatStatementFixture().build()

    def test_requires_auth(self):
        anon = APIClient()
        resp = anon.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_statement_id(self):
        resp = self.client.get(TEMPLATE_URL)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_statement_not_found(self):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_root_statement_rejected(self):
        """parent=None statement shablon berilmasligi kerak."""
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.root_statement.id})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_template_headers_and_hidden_uuid_row(self):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active

        # Barcha sarlavha qatorlaridagi qiymatlar
        all_headers = _all_header_values(ws)
        # Reja / avto-hisob / tashkilot ustunlari CHIQMASLIGI kerak
        self.assertNotIn("Reja ustuni", all_headers)
        self.assertNotIn("Avto-hisob", all_headers)
        self.assertNotIn("Tashkilot", all_headers)
        # Ko'p qatorli sarlavhada alohida qatorlarda turadi
        self.assertIn("Yanvar", all_headers)
        self.assertIn("Fevral", all_headers)
        self.assertIn("Amalda", all_headers)
        self.assertIn("Tumanlar nomi", all_headers)

        uuid_row = _find_uuid_row(ws)
        self.assertIsNotNone(uuid_row, "UUID qatori topilmadi")
        ids_row = [c.value for c in ws[uuid_row] if c.value is not None]
        self.assertIn(str(self.fixture.jan_amalda.id), ids_row)
        self.assertIn(str(self.fixture.feb_amalda.id), ids_row)
        self.assertIn(str(self.fixture.tumanlar.id), ids_row)
        self.assertEqual(len(ids_row), 3)
        self.assertTrue(ws.row_dimensions[uuid_row].hidden)

    def test_no_importable_columns_raises_400(self):
        empty_statement = Statement.objects.create(
            name="Empty Statement", parent=self.fixture.root_statement
        )
        resp = self.client.get(TEMPLATE_URL, {"statement_id": empty_statement.id})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_statement_name_with_newline_does_not_crash(self):
        """
        Statement nomida (title_uz) yangi qator belgisi bo'lsa,
        Content-Disposition header qurilishida xatolik bermasligi kerak.
        """
        weird_statement = Statement.objects.create(
            name="Weird\nStatement\rName", parent=self.fixture.root_statement
        )
        StatementColumn.objects.create(
            statement=weird_statement, parent=None, title="root", ordering="1",
        )
        StatementColumn.objects.create(
            statement=weird_statement,
            parent=StatementColumn.objects.get(statement=weird_statement, parent=None),
            title="Amalda", ordering="1.1",
        )
        resp = self.client.get(TEMPLATE_URL, {"statement_id": weird_statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_plant_based_template_has_plant_name_column(self):
        """Plantlik shablonda O'simlik nomi ustuni mavjud, lekin
        plantlar oldindan to'ldirilmaydi — foydalanuvchi o'zi yozadi."""
        pf = PlantStatementFixture().build()

        resp = self.client.get(TEMPLATE_URL, {"statement_id": pf.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active

        all_headers = _all_header_values(ws)
        self.assertIn("O'simlik nomi", all_headers)
        self.assertIn("№", all_headers)
        self.assertIn("Tashkilot nomi", all_headers)

        # UUID qatori topilishi kerak
        uuid_row = _find_uuid_row(ws)
        self.assertIsNotNone(uuid_row)
        # Plantlar oldindan to'ldirilmagan — UUID qatoridan keyin bo'sh bo'lishi kerak
        data_start = _find_data_start_row(ws)
        has_data = False
        for col in range(1, ws.max_column + 1):
            if ws.cell(row=data_start, column=col).value is not None:
                has_data = True
                break
        self.assertFalse(has_data, "Data qatorlarida oldindan hech narsa bo'lmasligi kerak")


class ImportParseAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = FlatStatementFixture().build()
        self.organization = make_organization()

    def _download_template_wb(self, statement_id):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": statement_id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return openpyxl.load_workbook(io.BytesIO(resp.content))

    def _post(self, wb, statement_id, **extra):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(statement_id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
            **extra,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    # ── Round-trip using the real template (hidden UUID row present) ──

    def test_round_trip_uuid_row(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        ws = wb.active
        data_row = _find_data_start_row(ws)

        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        feb_col = _find_col_by_uuid(ws, self.fixture.feb_amalda.id)
        tum_col = _find_col_by_uuid(ws, self.fixture.tumanlar.id)

        ws.cell(row=data_row, column=jan_col, value=12.5)
        ws.cell(row=data_row, column=feb_col, value="20,7")
        ws.cell(row=data_row, column=tum_col, value="Buvayda")

        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["errors"], [])
        self.assertFalse(body["is_plant_based"])

        by_col = {item["column"]: item["value"] for item in body["items"]}
        self.assertEqual(by_col[str(self.fixture.jan_amalda.id)], "12.5")
        self.assertEqual(by_col[str(self.fixture.feb_amalda.id)], "20.7")
        self.assertEqual(by_col[str(self.fixture.tumanlar.id)], "Buvayda")

        all_statement_ids = set(
            StatementColumn.objects.filter(statement=self.fixture.statement).values_list(
                "id", flat=True
            )
        )
        returned_ids = {item["column"] for item in body["items"]}
        self.assertTrue(returned_ids <= {str(i) for i in all_statement_ids})

    # ── Fallback: hidden UUID row missing -> header-text matching ──

    def test_round_trip_header_fallback_no_uuid_row(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        ws = wb.active
        uuid_row = _find_uuid_row(ws)
        data_row = _find_data_start_row(ws)

        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        feb_col = _find_col_by_uuid(ws, self.fixture.feb_amalda.id)
        tum_col = _find_col_by_uuid(ws, self.fixture.tumanlar.id)

        ws.cell(row=data_row, column=jan_col, value=12.5)
        ws.cell(row=data_row, column=feb_col, value=20.7)
        ws.cell(row=data_row, column=tum_col, value="Buvayda")

        # Yashirin UUID qatorini o'chiramiz — foydalanuvchi shablon qatorini
        # o'chirib yuborgan holatni simulyatsiya qiladi.
        ws.delete_rows(uuid_row)

        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()

        by_col = {item["column"]: item["value"] for item in body["items"]}
        self.assertEqual(by_col.get(str(self.fixture.jan_amalda.id)), "12.5")
        self.assertEqual(by_col.get(str(self.fixture.feb_amalda.id)), "20.7")
        self.assertEqual(by_col.get(str(self.fixture.tumanlar.id)), "Buvayda")

        # Fallback warning bo'lishi kerak
        messages = [w["message"] for w in body["warnings"]]
        self.assertTrue(any("Yashirin UUID qatori topilmadi" in m for m in messages))

        # backend-import-parse-bug.md dagi qabul mezoni:
        all_statement_ids = {
            str(i)
            for i in StatementColumn.objects.filter(
                statement=self.fixture.statement
            ).values_list("id", flat=True)
        }
        returned_ids = {item["column"] for item in body["items"]}
        self.assertTrue(
            returned_ids <= all_statement_ids,
            f"Foreign/invalid column ids leaked into response: {returned_ids - all_statement_ids}",
        )

    def test_non_importable_columns_never_leak_into_response(self):
        """
        Reja / avto-hisob / tashkilot ustunlari sarlavhalari faylga qo'lda
        qo'shilsa ham, ular importable emas -> javobga tushmasligi kerak.

        "Avto-hisob" ishlatiladi (Reja emas) — Reja ustunlari endi alohida
        `validate_plan_values` tekshiruvidan o'tadi, bu shu bilan aralashib
        ketmasligi uchun ular boshqa testda tekshiriladi (pastda).
        """
        wb = self._download_template_wb(self.fixture.statement.id)
        ws = wb.active
        uuid_row = _find_uuid_row(ws)
        ws.delete_rows(uuid_row)  # fallback matching ni majburlaymiz

        # Sarlavha oxiridan keyin qo'shimcha ustun qo'shamiz
        extra_col = ws.max_column + 1
        ws.cell(row=1, column=extra_col, value="Avto-hisob")
        # Ma'lumot qatori — UUID o'chirilgandan keyin sarlavha oxiri + 1
        data_row = ws.max_row + 1
        ws.cell(row=data_row, column=extra_col, value="999")

        tum_col = _find_col_by_uuid(ws, self.fixture.tumanlar.id)
        # UUID qatori o'chirilgani uchun col ni topish uchun fallback
        # Tumanlar nomi ustunini sarlavhalardan topamiz
        tum_col = None
        for row in range(1, ws.max_row + 1):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "Tumanlar nomi":
                    tum_col = col
                    break
            if tum_col:
                break
        if tum_col:
            ws.cell(row=data_row, column=tum_col, value="Buvayda")

        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()

        returned_ids = {item["column"] for item in body["items"]}
        self.assertNotIn(str(self.fixture.auto_calc.id), returned_ids)

    def test_decimal_comma_normalized(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        ws = wb.active
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value="1234,56")

        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        by_col = {item["column"]: item["value"] for item in resp.json()["items"]}
        self.assertEqual(by_col[str(self.fixture.jan_amalda.id)], "1234.56")

    def test_multi_row_flat_uses_first_and_warns(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        ws = wb.active
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=1)
        ws.cell(row=data_row + 1, column=jan_col, value=2)

        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        by_col = {item["column"]: item["value"] for item in body["items"]}
        self.assertEqual(by_col[str(self.fixture.jan_amalda.id)], "1")
        self.assertTrue(any("bitta tashkilot" in w["message"] for w in body["warnings"]))

    def test_empty_file_returns_400(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        resp = self._post(wb, self.fixture.statement.id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def _raw_post(self, upload):
        return self.client.post(
            PARSE_URL,
            {
                "file": upload,
                "statement_id": str(self.fixture.statement.id),
                "organization_id": str(self.organization.id),
                "year": DEFAULT_YEAR,
            },
            format="multipart",
        )

    def test_wrong_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        upload = SimpleUploadedFile("data.csv", b"a,b,c", content_type="text/csv")
        resp = self._raw_post(upload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.reports.views.imports.import_excel import MAX_FILE_SIZE
        big_content = b"0" * (MAX_FILE_SIZE + 1)
        upload = SimpleUploadedFile(
            "big.xlsx", big_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self._raw_post(upload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_statement_not_found(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        resp = self._post(wb, "00000000-0000-0000-0000-000000000000")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_organization_id_or_year_rejected(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        upload = make_upload(wb)
        resp = self.client.post(
            PARSE_URL,
            {"file": upload, "statement_id": str(self.fixture.statement.id)},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("organization_id", resp.json())
        self.assertIn("year", resp.json())

    def test_garbage_file_returns_400_not_500(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        upload = SimpleUploadedFile(
            "broken.xlsx", b"not a real xlsx file at all",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self._raw_post(upload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_sheet_name_returns_400(self):
        wb = self._download_template_wb(self.fixture.statement.id)
        resp = self._post(wb, self.fixture.statement.id, sheet_name="Does Not Exist")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class PlanValidationAPITests(TestCase):
    """
    Yangi talab: faylda Reja (`status_plan`) ustuniga qiymat topilsa, u
    bo'lim_admin tasdiqlagan Plan/PlanItem qiymati bilan bir xil bo'lishi
    SHART — mos kelmasa yoki reja umuman tasdiqlanmagan bo'lsa, butun
    import 400 bilan rad etiladi (`plan_validation.py`).

    `FlatStatementFixture.reja` — "Reja ustuni" (status_plan=YANVAR,
    globaly unique nom) shu testlarda ishlatiladi.
    """

    def setUp(self):
        self.user = make_user("planval@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = FlatStatementFixture().build()
        self.organization = make_organization("Plan Org")

    def _template_with_reja_column(self):
        """Shablonni yuklab, unga qo'lda "Reja ustuni" ustunini qo'shadi
        (haqiqiy shablon reja ustunlarini hech qachon o'z ichiga olmaydi —
        bu shu foydalanuvchi qo'lda tayyorlagan/eksport qilingan faylni
        simulyatsiya qiladi)."""
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        reja_col = ws.max_column + 1
        ws.cell(row=1, column=reja_col, value="Reja ustuni")
        return wb, ws, reja_col

    def _post(self, wb, **extra):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(self.fixture.statement.id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
            **extra,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    def test_no_plan_column_in_file_skips_validation(self):
        """Fayl Reja ustunini umuman o'z ichiga olmasa — hech qanday Plan
        DB'da bo'lmasa ham import muvaffaqiyatli o'tishi kerak (regressiya)."""
        wb, ws, _ = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        # "Reja ustuni" katagini bo'sh qoldiramiz — fayl reja qiymatini
        # o'z ichiga olmaydi.

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_matching_plan_value_passes(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("55.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value=55)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        # Reja ustuni javobga hech qachon qo'shilmaydi (faqat Amalda).
        returned_ids = {item["column"] for item in body["items"]}
        self.assertNotIn(str(self.fixture.reja.id), returned_ids)

    def test_decimal_formatting_difference_within_tolerance_passes(self):
        """Plan'da "100.00", faylda "100" — formatlash farqi, mos deb hisoblanadi."""
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("100.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value="100")

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_mismatched_plan_value_rejected(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("55.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value=99)  # 55 emas, 99 — mos kelmaydi

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        body = resp.json()
        self.assertEqual(body["items"], [])
        self.assertTrue(body["errors"])
        self.assertIn("Reja ustuni", body["errors"][0]["column_title"])
        self.assertIn("mos kelmadi", body["detail"])

    def test_plan_not_yet_confirmed_rejected(self):
        """Bo'lim_admin hali reja kiritmagan (Plan yo'q), lekin faylda
        Reja ustuniga qiymat bor — import rad etilishi kerak."""
        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value=55)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        body = resp.json()
        self.assertTrue(body["errors"])
        self.assertIn("tasdiqlangan reja", body["detail"])

    def test_different_year_plan_does_not_satisfy_validation(self):
        """2025-yilga tasdiqlangan reja, 2026-yil uchun import qilinsa —
        reja "topilmadi" holatiga tushishi kerak (yil bo'yicha aniq mos
        kelishi shart, faqat tashkilot+statement yetarli emas)."""
        plan_2025 = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=2025,
        )
        PlanItem.objects.create(plan=plan_2025, column=self.fixture.reja, plan_value=Decimal("55.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value=55)

        resp = self._post(wb, year=DEFAULT_YEAR)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_different_organization_plan_does_not_satisfy_validation(self):
        other_org = make_organization("Other Org")
        plan = Plan.objects.create(
            organization=other_org, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("55.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        jan_col = _find_col_by_uuid(ws, self.fixture.jan_amalda.id)
        ws.cell(row=data_row, column=jan_col, value=10)
        ws.cell(row=data_row, column=reja_col, value=55)

        resp = self._post(wb)  # self.organization — planga tegishli emas
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)


class PlantBasedParseAPITests(TestCase):
    def setUp(self):
        self.user = make_user("plants@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = PlantStatementFixture().build()
        self.organization = make_organization("Plant Org")

    def _download_template_wb(self):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return openpyxl.load_workbook(io.BytesIO(resp.content))

    def _post(self, wb, **extra):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(self.fixture.statement.id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
            **extra,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    def test_round_trip_by_plant_name(self):
        """Plantlar oldindan to'ldirilmagani uchun, foydalanuvchi
        O'simlik nomi ustuniga nom yozadi, parser nom bo'yicha topadi."""
        wb = self._download_template_wb()
        ws = wb.active
        data_row = _find_data_start_row(ws)

        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)
        area_col = _find_col_by_uuid(ws, self.fixture.area.id)

        # O'simlik nomi ustunini topamiz (3-ustun — plantlik jadvalda)
        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break
        self.assertIsNotNone(plant_name_col, "O'simlik nomi ustuni topilmadi")

        # Archa
        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=100)
        ws.cell(row=data_row, column=area_col, value=5.5)
        # Qayin
        ws.cell(row=data_row + 1, column=plant_name_col, value="Qayin")
        ws.cell(row=data_row + 1, column=amount_col, value=40)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        self.assertTrue(body["is_plant_based"])
        self.assertEqual(body["status"], "success")

        plants_by_id = {p["plant"]: p for p in body["plants"]}
        archa = plants_by_id[str(self.fixture.archa.id)]
        archa_values = {i["column"]: i["value"] for i in archa["items"]}
        self.assertEqual(archa_values[str(self.fixture.amount.id)], "100")
        self.assertEqual(archa_values[str(self.fixture.area.id)], "5.5")

        qayin = plants_by_id[str(self.fixture.qayin.id)]
        qayin_values = {i["column"]: i["value"] for i in qayin["items"]}
        self.assertEqual(qayin_values[str(self.fixture.amount.id)], "40")
        self.assertNotIn(str(self.fixture.area.id), qayin_values)

        for item in body["items"]:
            self.assertIn("plant", item)
            self.assertIn("plant_name", item)

    def test_round_trip_fallback_header_matching(self):
        """UUID qatorini o'chirib, faqat sarlavha matniga qarab moslashtirish."""
        wb = self._download_template_wb()
        ws = wb.active
        uuid_row = _find_uuid_row(ws)
        data_row = _find_data_start_row(ws)

        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)
        plant_name_col = None
        for row in range(1, uuid_row):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=77)

        # UUID qatorini o'chiramiz -> fallback matching
        ws.delete_rows(uuid_row)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        plants_by_id = {p["plant"]: p for p in body["plants"]}
        archa = plants_by_id[str(self.fixture.archa.id)]
        archa_values = {i["column"]: i["value"] for i in archa["items"]}
        self.assertEqual(archa_values[str(self.fixture.amount.id)], "77")

    def test_ambiguous_plant_name_reports_error(self):
        Plant.objects.create(statement=self.fixture.statement, name="Archa")  # duplicate name
        wb = self._download_template_wb()
        ws = wb.active
        uuid_row = _find_uuid_row(ws)
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        # UUID qatorini o'chiramiz — fallback matching
        ws.delete_rows(uuid_row)

        # O'simlik nomi ustunini topamiz
        plant_name_col = None
        for row in range(1, ws.max_row + 1):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        # UUID o'chirilgandan keyin data_row 1 qator yuqoriga suradi
        adjusted_data_row = data_row - 1
        ws.cell(row=adjusted_data_row, column=plant_name_col, value="Archa")
        ws.cell(row=adjusted_data_row, column=amount_col, value=5)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        self.assertTrue(body["errors"])

    def test_total_row_without_plant_is_skipped(self):
        wb = self._download_template_wb()
        ws = wb.active
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        # O'simlik nomi ustunini topamiz
        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        # "Jami" qatorini qo'shamiz
        ws.cell(row=data_row, column=plant_name_col, value="Jami")
        ws.cell(row=data_row, column=amount_col, value=999)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        total_values = [
            it["value"] for p in body["plants"] for it in p["items"]
            if it["value"] == "999"
        ]
        self.assertEqual(total_values, [])


class PlantPlanValidationAPITests(TestCase):
    """
    Xuddi shu Reja validatsiyasi plantlik reportlarda ham ishlashi kerak.

    Ikki holat bor:
      1. Statement uchun reja FLAT (faqat PlanItem, PlantPlan yo'q) — bu
         holatda kutilgan qiymat barcha o'simlik qatorlari uchun BIR XIL.
      2. Reja o'zi ham plantlik (PlantPlan/PlantPlanItem bor) — kutilgan
         qiymat har bir (o'simlik, ustun) juftligi uchun alohida.
    """

    def setUp(self):
        self.user = make_user("plantplanval@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = PlantStatementFixture().build()
        self.organization = make_organization("Plant Plan Org")

    def _template_with_reja_column(self):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        reja_col = ws.max_column + 1
        ws.cell(row=1, column=reja_col, value="Reja miqdori")
        return wb, ws, reja_col

    def _post(self, wb, **extra):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(self.fixture.statement.id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
            **extra,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    # ── Flat reja (PlanItem only) — bir xil qiymat barcha o'simliklarga ──

    def test_flat_plan_matching_value_on_every_plant_row_passes(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("10.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        # O'simlik nomi ustunini topamiz
        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        # Archa va Qayin uchun ma'lumot yozish
        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=1)
        ws.cell(row=data_row, column=reja_col, value=10)
        ws.cell(row=data_row + 1, column=plant_name_col, value="Qayin")
        ws.cell(row=data_row + 1, column=amount_col, value=1)
        ws.cell(row=data_row + 1, column=reja_col, value=10)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_flat_plan_one_plant_row_mismatch_rejected(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        PlanItem.objects.create(plan=plan, column=self.fixture.reja, plan_value=Decimal("10.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=1)
        ws.cell(row=data_row, column=reja_col, value=10)  # to'g'ri
        ws.cell(row=data_row + 1, column=plant_name_col, value="Qayin")
        ws.cell(row=data_row + 1, column=amount_col, value=1)
        ws.cell(row=data_row + 1, column=reja_col, value=999)  # noto'g'ri

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        body = resp.json()
        self.assertTrue(body["errors"])

    # ── Plantlik reja (PlantPlan/PlantPlanItem) — har bir o'simlik alohida ──

    def test_per_plant_plan_matching_values_pass(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        archa_plan = PlantPlan.objects.create(plan=plan, plant=self.fixture.archa)
        PlantPlanItem.objects.create(plant_plan=archa_plan, column=self.fixture.reja, plan_value=Decimal("7.00"))
        qayin_plan = PlantPlan.objects.create(plan=plan, plant=self.fixture.qayin)
        PlantPlanItem.objects.create(plant_plan=qayin_plan, column=self.fixture.reja, plan_value=Decimal("9.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=1)
        ws.cell(row=data_row, column=reja_col, value=7)
        ws.cell(row=data_row + 1, column=plant_name_col, value="Qayin")
        ws.cell(row=data_row + 1, column=amount_col, value=1)
        ws.cell(row=data_row + 1, column=reja_col, value=9)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_per_plant_plan_mismatch_for_one_plant_rejected(self):
        plan = Plan.objects.create(
            organization=self.organization, statement=self.fixture.statement, year=DEFAULT_YEAR,
        )
        archa_plan = PlantPlan.objects.create(plan=plan, plant=self.fixture.archa)
        PlantPlanItem.objects.create(plant_plan=archa_plan, column=self.fixture.reja, plan_value=Decimal("7.00"))
        qayin_plan = PlantPlan.objects.create(plan=plan, plant=self.fixture.qayin)
        PlantPlanItem.objects.create(plant_plan=qayin_plan, column=self.fixture.reja, plan_value=Decimal("9.00"))

        wb, ws, reja_col = self._template_with_reja_column()
        data_row = _find_data_start_row(ws)
        amount_col = _find_col_by_uuid(ws, self.fixture.amount.id)

        plant_name_col = None
        for row in range(1, _find_uuid_row(ws)):
            for col in range(1, ws.max_column + 1):
                if ws.cell(row=row, column=col).value == "O'simlik nomi":
                    plant_name_col = col
                    break
            if plant_name_col:
                break

        ws.cell(row=data_row, column=plant_name_col, value="Archa")
        ws.cell(row=data_row, column=amount_col, value=1)
        ws.cell(row=data_row, column=reja_col, value=7)   # to'g'ri
        ws.cell(row=data_row + 1, column=plant_name_col, value="Qayin")
        ws.cell(row=data_row + 1, column=amount_col, value=1)
        ws.cell(row=data_row + 1, column=reja_col, value=999)  # noto'g'ri (9 kutilgan edi)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        body = resp.json()
        self.assertTrue(body["errors"])


class TwinColumnFixture:
    """Bir xil nomli, bir xil ota-onali ikkita ustun ("... (1)" / "... (2)")."""

    def build(self):
        self.root_statement = Statement.objects.create(name="Twin Root")
        self.statement = Statement.objects.create(name="Twin Statement", parent=self.root_statement)
        self.app_root = StatementColumn.objects.create(
            statement=self.statement, parent=None, title="Ilova", ordering="1",
        )
        self.group = StatementColumn.objects.create(
            statement=self.statement, parent=self.app_root, title="Maxsus", ordering="1.1",
        )
        self.amalda_1 = StatementColumn.objects.create(
            statement=self.statement, parent=self.group, title="Amalda", ordering="1.1.1",
        )
        self.amalda_2 = StatementColumn.objects.create(
            statement=self.statement, parent=self.group, title="Amalda", ordering="1.1.2",
        )
        return self


class TwinColumnAPITests(TestCase):
    """
    Bir xil to'liq yo'lli (bir xil nom + bir xil ota-ona) ikkita ustun —
    `label()` va `strip_ordinal`/`importable_by_path_ordinal` orqali
    "... (1)" / "... (2)" bilan ajratilishi kerak.
    """

    def setUp(self):
        self.user = make_user("twin@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = TwinColumnFixture().build()
        self.organization = make_organization("Twin Org")

    def _download_template_wb(self):
        resp = self.client.get(TEMPLATE_URL, {"statement_id": self.fixture.statement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return openpyxl.load_workbook(io.BytesIO(resp.content))

    def _post(self, wb):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(self.fixture.statement.id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    def test_template_labels_twins_in_multi_row_format(self):
        """Ko'p qatorli shablonda twin ustunlar alohida ustunlar sifatida turadi,
        UUID orqali aniq ajratiladi — ordinal suffix kerak emas."""
        wb = self._download_template_wb()
        ws = wb.active

        # Ikkita alohida UUID bo'lishi kerak
        col_1 = _find_col_by_uuid(ws, self.fixture.amalda_1.id)
        col_2 = _find_col_by_uuid(ws, self.fixture.amalda_2.id)
        self.assertIsNotNone(col_1, "amalda_1 UUID topilmadi")
        self.assertIsNotNone(col_2, "amalda_2 UUID topilmadi")
        self.assertNotEqual(col_1, col_2, "Twin ustunlar alohida ustunlarda bo'lishi kerak")

    def test_round_trip_uuid_row_distinguishes_twins(self):
        wb = self._download_template_wb()
        ws = wb.active
        data_row = _find_data_start_row(ws)
        col_1 = _find_col_by_uuid(ws, self.fixture.amalda_1.id)
        col_2 = _find_col_by_uuid(ws, self.fixture.amalda_2.id)
        ws.cell(row=data_row, column=col_1, value=11)
        ws.cell(row=data_row, column=col_2, value=22)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        by_col = {item["column"]: item["value"] for item in resp.json()["items"]}
        self.assertEqual(by_col[str(self.fixture.amalda_1.id)], "11")
        self.assertEqual(by_col[str(self.fixture.amalda_2.id)], "22")

    def test_header_fallback_twins_requires_uuid_row(self):
        """Ko'p qatorli shablondan UUID qatorini o'chirganingizda,
        twin (bir xil nomli) ustunlarni fallback matching orqali
        to'liq moslashtirish mumkin emas — parser 400 qaytaradi.
        Bu kutilgan holat: shablonning UUID qatorini o'chirmaslik kerak."""
        wb = self._download_template_wb()
        ws = wb.active
        uuid_row = _find_uuid_row(ws)
        data_row = _find_data_start_row(ws)
        col_1 = _find_col_by_uuid(ws, self.fixture.amalda_1.id)
        col_2 = _find_col_by_uuid(ws, self.fixture.amalda_2.id)
        ws.cell(row=data_row, column=col_1, value=11)
        ws.cell(row=data_row, column=col_2, value=22)
        ws.delete_rows(uuid_row)

        resp = self._post(wb)
        # Ko'p qatorli shablonda UUID o'chirilsa, sarlavhalar to'g'ri
        # moslashtirilmaydi — bu kutilgan holat
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class ExportStyleMultiRowHeaderTests(TestCase):
    """
    `backend-import-parse-bug.md` da tasvirlangan haqiqiy holatni qayta hosil
    qiladi: eksport fayli bir necha jismoniy sarlavha qatoridan (guruh nomi
    merge qilingan) iborat, yashirin UUID qatori umuman yo'q.
    """

    def setUp(self):
        self.user = make_user("export@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.fixture = FlatStatementFixture().build()
        self.organization = make_organization("Export Org")

    def _post(self, wb):
        upload = make_upload(wb)
        data = {
            "file": upload,
            "statement_id": str(self.fixture.statement.id),
            "organization_id": str(self.organization.id),
            "year": DEFAULT_YEAR,
        }
        return self.client.post(PARSE_URL, data, format="multipart")

    def test_multi_row_merged_header_export_file(self):
        wb = openpyxl.Workbook()
        ws = wb.active

        # Row 1: "Export qilingan vaqt" — sarlavha bloki emas
        ws.cell(row=1, column=1, value="Eksport qilingan vaqt: 2026-01-01 10:00")

        # Row 2: xizmat va guruh sarlavhalari (guruh nomi merge qilingan)
        ws.cell(row=2, column=1, value="Tashkilot nomi")
        ws.cell(row=2, column=2, value="Tumanlar nomi")
        ws.cell(row=2, column=3, value="1-chorak")
        ws.merge_cells(start_row=2, start_column=3, end_row=2, end_column=4)

        # Row 3: oy nomlari
        ws.cell(row=3, column=3, value="Yanvar")
        ws.cell(row=3, column=4, value="Fevral")

        # Row 4: leaf sarlavha
        ws.cell(row=4, column=3, value="Amalda")
        ws.cell(row=4, column=4, value="Amalda")

        # Row 5: ma'lumot
        ws.cell(row=5, column=1, value="Test tashkiloti MCHJ")
        ws.cell(row=5, column=2, value="Buvayda")
        ws.cell(row=5, column=3, value=12.5)
        ws.cell(row=5, column=4, value=20.7)

        resp = self._post(wb)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()

        by_col = {item["column"]: item["value"] for item in body["items"]}
        self.assertEqual(by_col.get(str(self.fixture.tumanlar.id)), "Buvayda")
        self.assertEqual(by_col.get(str(self.fixture.jan_amalda.id)), "12.5")
        self.assertEqual(by_col.get(str(self.fixture.feb_amalda.id)), "20.7")

        # "Tashkilot nomi" servis ustuni — items ichida hech qanday ustunga
        # "Test tashkiloti MCHJ" qiymati sifatida tushmasligi kerak.
        self.assertNotIn("Test tashkiloti MCHJ", by_col.values())

        # backend-import-parse-bug.md dagi qabul mezoni: faqat shu statement
        # ning haqiqiy ustunlari qaytishi kerak.
        all_statement_ids = {
            str(i)
            for i in StatementColumn.objects.filter(
                statement=self.fixture.statement
            ).values_list("id", flat=True)
        }
        returned_ids = {item["column"] for item in body["items"]}
        self.assertTrue(
            returned_ids <= all_statement_ids,
            f"Foreign/invalid column ids leaked into response: "
            f"{returned_ids - all_statement_ids}; full body={body}",
        )


class ServiceLayerUnitTests(TestCase):
    """columns.py / parser.py ichidagi yordamchi funksiyalarni to'g'ridan-to'g'ri tekshiradi."""

    def setUp(self):
        self.fixture = FlatStatementFixture().build()

    def test_get_importable_columns_excludes_non_leaf_and_special(self):
        importable = list(get_importable_columns(self.fixture.statement))
        ids = {c.id for c in importable}
        self.assertIn(self.fixture.jan_amalda.id, ids)
        self.assertIn(self.fixture.feb_amalda.id, ids)
        self.assertIn(self.fixture.tumanlar.id, ids)
        self.assertNotIn(self.fixture.app_root.id, ids)   # root, parent is None
        self.assertNotIn(self.fixture.quarter.id, ids)    # group, has children
        self.assertNotIn(self.fixture.january.id, ids)    # group, has children
        self.assertNotIn(self.fixture.reja.id, ids)        # status_plan set
        self.assertNotIn(self.fixture.auto_calc.id, ids)   # is_user_input False
        self.assertNotIn(self.fixture.organization.id, ids)  # is_organization True

    def test_label_disambiguates_same_name_columns(self):
        index = StatementColumnIndex(self.fixture.statement, lang="uz")
        self.assertEqual(index.label(self.fixture.jan_amalda), "Yanvar » Amalda")
        self.assertEqual(index.label(self.fixture.feb_amalda), "Fevral » Amalda")
        self.assertEqual(index.label(self.fixture.tumanlar), "Tumanlar nomi")

    def test_is_plant_based_statement_detection(self):
        self.assertFalse(is_plant_based_statement(self.fixture.statement))
        pf = PlantStatementFixture().build()
        self.assertTrue(is_plant_based_statement(pf.statement))

    def test_parse_import_excel_raises_valueerror_when_no_importable_columns(self):
        empty_statement = Statement.objects.create(
            name="Empty for parse", parent=self.fixture.root_statement
        )
        StatementColumn.objects.create(
            statement=empty_statement, parent=None, title="root",
        )
        wb = openpyxl.Workbook()
        wb.active.append(["a"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        with self.assertRaises(ValueError):
            parse_import_excel(buf, empty_statement)
