import os
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, ReportItem, ReportItemInner, Statement, StatementColumn
from apps.reports.services.manual_repots.formula import FormulaError, evaluate_formula
from apps.reports.services.manual_repots.simple_reports import calculate_normal_by_expressions


def _column(values):
    return lambda ordering: Decimal(values[ordering])


class FormulaEvaluatorTest(TestCase):
    """Audit A8: Statement.calculate_expression eval() bilan emas, cheklangan parser bilan hisoblanadi."""

    def test_arithmetic_with_columns(self):
        col = _column({"1.1.5": "50", "1.1.4": "200"})
        self.assertEqual(evaluate_formula("column('1.1.5') / column('1.1.4') * 100", col), Decimal("25"))
        self.assertEqual(evaluate_formula('(column("1.1.5") + 10) - 2 * 5', col), Decimal("50"))
        self.assertEqual(evaluate_formula("-column('1.1.5') + Decimal('0.5')", col), Decimal("-49.5"))

    def test_attribute_access_is_rejected(self):
        with self.assertRaises(FormulaError):
            evaluate_formula("().__class__.__base__.__subclasses__()", _column({}))

    def test_unknown_names_and_calls_are_rejected(self):
        for expr in ("__import__('os')", "open('/etc/passwd')", "x + 1", "column('1').real", "column(1)",
                     "column('1', 2)", "column(ordering='1')", "[c for c in ()]", "1 if 1 else 2", "1 == 1"):
            with self.subTest(expr=expr), self.assertRaises(FormulaError):
                evaluate_formula(expr, _column({"1": "1"}))


class FormulaEndToEndTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="T", region="tashkent")
        dept = Statement.objects.create(name="Bo'lim")
        cls.stmt = Statement.objects.create(name="Shakl", parent=dept)
        for o in ("1", "2", "3"):
            StatementColumn.objects.create(statement=cls.stmt, title=o, title_uz=o, title_ru=o, ordering=o)
        cls.deadline = Deadline.objects.create(statement=cls.stmt, submit_at="2026")

    def _report(self, expression):
        self.stmt.calculate_expression = expression
        self.stmt.save(update_fields=["calculate_expression"])
        report = Report.objects.create(organization=self.org, statement=self.stmt, deadline=self.deadline)
        cols = {c.ordering: c for c in self.stmt.statement_columns.all()} if hasattr(self.stmt, "statement_columns") \
            else {c.ordering: c for c in StatementColumn.objects.filter(statement=self.stmt)}
        for ordering, value in (("1", "30"), ("2", "120")):
            item = ReportItem.objects.create(report=report, statement_column=cols[ordering])
            ReportItemInner.objects.create(report_item=item, value=value)
        return report

    def _target_values(self, report):
        return [i.value for i in ReportItemInner.objects.filter(
            report_item__report=report, report_item__statement_column__ordering="3")]

    def test_formula_fills_target_column(self):
        report = self._report("column('1') / column('2') * 100 = column('3')")
        calculate_normal_by_expressions(report)
        self.assertEqual(self._target_values(report), ["25.00"])

    def test_malicious_expression_is_not_executed(self):
        marker = os.path.join(tempfile.gettempdir(), "stat_urmon_formula_rce")
        if os.path.exists(marker):
            os.remove(marker)
        payload = ("[c for c in ().__class__.__base__.__subclasses__() if 'BuiltinImporter' in c.__name__][0]"
                   f".load_module('os').system('touch {marker}') + column('1') = column('3')")
        report = self._report(payload)
        calculate_normal_by_expressions(report)
        self.assertFalse(os.path.exists(marker))
        # Noto'g'ri formula umuman bajarilmaydi — target ustun to'ldirilmaydi
        self.assertEqual(self._target_values(report), [])


class StatementFormulaValidationTest(TestCase):
    def test_invalid_formula_is_rejected_on_clean(self):
        stmt = Statement(name="S", calculate_expression="().__class__ = column('3')")
        with self.assertRaises(ValidationError):
            stmt.full_clean()

    def test_valid_formula_passes_clean(self):
        stmt = Statement(name="S", calculate_expression="column('1') / column('2') * 100 = column('3')\n\n")
        stmt.full_clean()
