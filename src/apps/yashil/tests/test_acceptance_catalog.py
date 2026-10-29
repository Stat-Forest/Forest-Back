"""Qabul sinovlari katalogi (TZ §18–19): Q01–Q36 to'liq, har avtomatik sinov mavjud testga bog'langan."""
import importlib

from django.test import SimpleTestCase

from apps.yashil.acceptance import CASES, all_test_labels


class AcceptanceCatalogTest(SimpleTestCase):
    def test_all_36_cases_in_order(self):
        self.assertEqual([c.id for c in CASES], [f"Q{i:02d}" for i in range(1, 37)])
        for c in CASES:
            self.assertTrue(c.title and c.expected and c.role and c.manual, c.id)

    def test_q01_to_q34_have_tests_and_q35_q36_have_tools(self):
        for c in CASES:
            if c.id in ("Q35", "Q36"):
                self.assertTrue(c.tools, c.id)
            else:
                self.assertTrue(c.tests, c.id)

    def test_every_referenced_test_exists(self):
        for label in all_test_labels():
            module, cls, method = label.rsplit(".", 2)
            klass = getattr(importlib.import_module(module), cls, None)
            self.assertIsNotNone(klass, label)
            self.assertTrue(callable(getattr(klass, method, None)), label)


class ProtocolDocxTest(SimpleTestCase):
    def test_protocol_has_row_per_case_and_shows_results(self):
        from apps.yashil.services.protocol import FAIL, OK, build_protocol_docx, case_summary

        results = {f"apps.yashil.tests.{t}": {"status": OK} for c in CASES for t in c.tests}
        first = f"apps.yashil.tests.{CASES[0].tests[0]}"
        results[first] = {"status": FAIL}
        self.assertEqual(case_summary(CASES[0], results)["status"], FAIL)
        self.assertEqual(case_summary(CASES[1], results)["status"], OK)
        self.assertEqual(case_summary(CASES[35], results)["status"], "manual")
        doc = build_protocol_docx(results, {"date": "29.10.2026", "environment": "lokal", "version": "abc123"})
        table = doc.tables[0]
        self.assertEqual(len(table.rows), 37)
        self.assertEqual(table.rows[1].cells[0].text, "Q01")
        self.assertIn("ўтмади", table.rows[1].cells[5].text)
        self.assertIn("ўтди", table.rows[2].cells[5].text)
        self.assertEqual(table.rows[36].cells[5].text, "—")
        text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("abc123", text)
        self.assertIn("34 та ҳолатдан 33 тасида", text)

    def test_blank_protocol_without_results(self):
        from apps.yashil.services.protocol import build_protocol_docx

        doc = build_protocol_docx(None, {"date": "29.10.2026"})
        self.assertEqual(len(doc.tables[0].rows), 37)
        self.assertIn("та тест", doc.tables[0].rows[1].cells[5].text)
