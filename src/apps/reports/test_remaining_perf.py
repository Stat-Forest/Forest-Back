"""
Qolgan tezlik ishlari: bekor qilish/o'chirish yo'li Celery'da, filtered kesh
versiyasi, Excel eksport so'rovlar soni.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, ReportItem, ReportItemInner, Statement, StatementColumn

User = get_user_model()
S = Report.StatusChoices


class _Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Statement.objects.create(name="Bo'lim R", name_uz="Bo'lim R", name_ru="Отдел R")
        cls.form = Statement.objects.create(name="Shakl R", name_uz="Shakl R", name_ru="Форма R", parent=cls.dept)
        cls.other_form = Statement.objects.create(name="Shakl R2", name_uz="Shakl R2", name_ru="Форма R2", parent=cls.dept)
        cls.deadline = Deadline.objects.create(statement=cls.form, submit_at="2026-05", deadline_at=timezone.localdate())
        cls.columns = [
            StatementColumn.objects.create(statement=cls.form, title=f"C{i}", title_uz=f"C{i}", title_ru=f"C{i}", ordering=str(i))
            for i in range(1, 4)
        ]
        cls.super_admin = User.objects.create_superuser(
            email="root_r@example.com", password="TestPassword123!", first_name="R", last_name="T",
        )

    def _org(self, i):
        o = Organization.objects.create(name=f"Org R{i}", name_uz=f"Org R{i}", region="tashkent")
        self.deadline.organizations.add(o)
        return o

    def _report(self, org, status=S.ACCEPTED, with_items=True):
        r = Report.objects.create(organization=org, statement=self.form, deadline=self.deadline,
                                  status=status, region="tashkent")
        if with_items:
            for col in self.columns:
                it = ReportItem.objects.create(report=r, statement_column=col)
                ReportItemInner.objects.create(report_item=it, value="3")
        return r


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class CancelDeleteSchedulingTest(_Base):
    def test_cancel_schedules_regional_totals_after_commit(self):
        from apps.reports.tasks.aggregation import aggregate_statement_totals
        with mock.patch.object(aggregate_statement_totals, "delay") as delay:
            r = self._report(self._org(1), with_items=False)
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                r.cancel("sabab")
                delay.assert_not_called()
            for cb in callbacks:
                cb()
            delay.assert_called_once_with(str(self.form.id), str(self.deadline.id), "tashkent")
        r.refresh_from_db()
        self.assertEqual(r.status, S.CANCELLED)

    def test_delete_schedules_regional_totals_after_commit(self):
        from apps.reports.tasks.aggregation import aggregate_statement_totals
        with mock.patch.object(aggregate_statement_totals, "delay") as delay:
            keep = self._report(self._org(1), with_items=False)
            gone = self._report(self._org(2), with_items=False)
            delay.reset_mock()
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                gone.delete()
                delay.assert_not_called()
            for cb in callbacks:
                cb()
            delay.assert_called_once_with(str(self.form.id), str(self.deadline.id), "tashkent")
        self.assertTrue(Report.objects.filter(id=keep.id).exists())


class FilteredCacheVersionTest(_Base):
    def test_report_save_changes_filtered_cache_key_for_its_statement(self):
        from apps.reports.services.report_cache import get_filtered_cache_key
        cache.clear()
        k_form = get_filtered_cache_key(str(self.form.id), str(self.deadline.id), "uz")
        k_other = get_filtered_cache_key(str(self.other_form.id), str(self.deadline.id), "uz")
        self._report(self._org(1), status=S.SAVED, with_items=False)
        self.assertNotEqual(k_form, get_filtered_cache_key(str(self.form.id), str(self.deadline.id), "uz"))
        self.assertEqual(k_other, get_filtered_cache_key(str(self.other_form.id), str(self.deadline.id), "uz"))

    def test_no_dead_cache_signals_module(self):
        import importlib.util
        self.assertIsNone(importlib.util.find_spec("apps.reports.signals.cache_signals"))


class ExportQueryTest(_Base):
    URL = "/api/v1/reports/export-excel/"

    def _export(self, reports):
        self.client.force_authenticate(self.super_admin)
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.post(self.URL, {"report_ids": [str(x.id) for x in reports], "lang": "uz", "mode": "json"},
                                 format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return len(ctx.captured_queries), ctx.captured_queries

    def test_query_count_does_not_grow_with_reports(self):
        small = [self._report(self._org(i)) for i in range(1, 3)]
        n_small, _ = self._export(small)
        big = small + [self._report(self._org(i)) for i in range(3, 8)]
        n_big, qs = self._export(big)
        self.assertEqual(n_small, n_big, "\n".join(q["sql"][:110] for q in qs))
