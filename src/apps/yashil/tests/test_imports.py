"""Excel import buyruqlari: mahallalar, biriktirishlar, kalendar (javoblar A1, A2, Д1, Е1)."""
import io
import tempfile
from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from apps.yashil.models import CalendarDay, Mahalla, SupplierAssignment
from apps.yashil.tests._common import make_district, make_forest, make_region


def xlsx(rows, header):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    return tmp.name


def run(cmd, *args):
    out = io.StringIO()
    call_command(cmd, *args, stdout=out, stderr=out)
    return out.getvalue()


class ImportMahallasTest(TestCase):
    def setUp(self):
        self.region = make_region("1703", "Андижон вилояти")
        self.district = make_district(self.region, "1703202", "Андижон тумани")
        self.header = ["манба коди", "вилоят коди", "туман коди", "маҳалла номи", "манзил", "фаол", "амал бошланиши"]

    def test_dry_run_reports_without_writing(self):
        path = xlsx([["MH-001", "1703", "1703202", "Боғистон", "Андижон ш.", "ҳа", "01.01.2026"]], self.header)
        out = run("yashil_import_mahallas", "--file", path, "--dry-run")
        self.assertEqual(Mahalla.objects.count(), 0)
        self.assertIn("yangi: 1", out)

    def test_import_is_idempotent_and_updates_by_source_code(self):
        path = xlsx([["MH-001", "1703", "1703202", "Боғистон", "Андижон ш.", "ҳа", "01.01.2026"]], self.header)
        run("yashil_import_mahallas", "--file", path)
        path2 = xlsx([["MH-001", "1703", "1703202", "Боғистон маҳалласи", "Андижон ш.", "ҳа", "01.01.2026"]], self.header)
        out = run("yashil_import_mahallas", "--file", path2)
        self.assertEqual(Mahalla.objects.count(), 1)
        self.assertEqual(Mahalla.objects.get().name, "Боғистон маҳалласи")
        self.assertIn("yangilandi: 1", out)

    def test_unknown_district_is_reported_and_skipped(self):
        path = xlsx([
            ["MH-001", "1703", "1703202", "Боғистон", "", "ҳа", ""],
            ["MH-002", "1703", "1703999", "Йўқ туман", "", "ҳа", ""],
        ], self.header)
        out = run("yashil_import_mahallas", "--file", path)
        self.assertEqual(Mahalla.objects.count(), 1)
        self.assertIn("3-qator", out)
        self.assertIn("1703999", out)
        # Xato matni interfeysda kirill ko'rinishida chiqadi (modul tili — TZ §17.1)
        self.assertIn("туман коди топилмади", out)

    def test_file_level_errors_are_cyrillic(self):
        from apps.yashil.services.imports import ImportFileError, import_mahallas

        path = xlsx([["MH-001", "Боғистон"]], ["манба коди", "маҳалла номи"])
        with self.assertRaises(ImportFileError) as cm:
            import_mahallas(path, dry_run=True)
        self.assertIn("Мажбурий устунлар топилмади", str(cm.exception))

    def test_latin_headers_are_accepted(self):
        header = ["manba kodi", "viloyat kodi", "tuman kodi", "mahalla nomi", "manzil", "faol", "amal boshlanishi"]
        path = xlsx([["MH-003", "1703", "1703202", "Навбаҳор", "", "yo'q", "2026-02-01"]], header)
        run("yashil_import_mahallas", "--file", path)
        m = Mahalla.objects.get(source_code="MH-003")
        self.assertFalse(m.is_active)
        self.assertEqual(m.valid_from, date(2026, 2, 1))


class ImportAssignmentsTest(TestCase):
    def setUp(self):
        district = make_district(make_region())
        self.mahalla = Mahalla.objects.create(name="Боғистон", region=district.region, district=district, source_code="MH-001")
        self.f1 = make_forest("F1")
        self.f2 = make_forest("F2")
        self.header = ["маҳалла коди", "хўжалик", "амал бошланиши", "амал тугаши"]

    def test_assign_by_org_id_and_by_name(self):
        path = xlsx([
            ["MH-001", str(self.f1.pk), "01.01.2026", "30.06.2026"],
            ["MH-001", "F2", "01.07.2026", ""],
        ], self.header)
        out = run("yashil_import_assignments", "--file", path)
        self.assertEqual(SupplierAssignment.objects.count(), 2)
        self.assertIn("yangi: 2", out)

    def test_overlap_is_rejected_with_row_number(self):
        path = xlsx([
            ["MH-001", "F1", "01.01.2026", ""],
            ["MH-001", "F2", "01.03.2026", ""],
        ], self.header)
        out = run("yashil_import_assignments", "--file", path)
        self.assertEqual(SupplierAssignment.objects.count(), 1)
        self.assertIn("3-qator", out)

    def test_reimport_of_same_row_is_not_duplicated(self):
        path = xlsx([["MH-001", "F1", "01.01.2026", ""]], self.header)
        run("yashil_import_assignments", "--file", path)
        out = run("yashil_import_assignments", "--file", path)
        self.assertEqual(SupplierAssignment.objects.count(), 1)
        self.assertIn("o'zgarishsiz: 1", out)


class ImportCalendarTest(TestCase):
    def test_import_holidays_and_moved_workdays(self):
        path = xlsx([
            ["01.01.2027", "байрам", "Янги йил"],
            ["09.01.2027", "иш куни", "Кўчирилган"],
            ["2027-03-08", "dam olish", "Xotin-qizlar kuni"],
        ], ["сана", "тури", "изоҳ"])
        out = run("yashil_import_calendar", "--file", path, "--source", "ВМ қарори №1")
        self.assertEqual(CalendarDay.objects.filter(kind="holiday").count(), 2)
        self.assertEqual(CalendarDay.objects.filter(kind="workday").count(), 1)
        self.assertEqual(CalendarDay.objects.get(date=date(2027, 1, 1)).source_ref, "ВМ қарори №1")
        run("yashil_import_calendar", "--file", path, "--source", "ВМ қарори №1")
        self.assertEqual(CalendarDay.objects.count(), 3)
        self.assertIn("yangi: 3", out)
