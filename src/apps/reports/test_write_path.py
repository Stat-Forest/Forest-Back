"""
Yozish yo'li: hisobot yangilash, Report.save, signal'lar, accept → aggregatsiya.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.models.signals import post_delete, post_save
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
        cls.dept = Statement.objects.create(name="Bo'lim W", name_uz="Bo'lim W", name_ru="Отдел W")
        cls.form = Statement.objects.create(name="Shakl W", name_uz="Shakl W", name_ru="Форма W", parent=cls.dept)
        cls.org = Organization.objects.create(name="Tashkilot W", name_uz="Tashkilot W", region="tashkent")
        cls.deadline = Deadline.objects.create(statement=cls.form, submit_at="2026-03", deadline_at=timezone.localdate())
        cls.deadline.organizations.add(cls.org)
        cls.columns = [
            StatementColumn.objects.create(statement=cls.form, title=f"U{i}", title_uz=f"U{i}", title_ru=f"U{i}", ordering=str(i))
            for i in range(1, 9)
        ]
        cls.hodim = User.objects.create_user(
            email="hodim_w@example.com", password="TestPassword123!", first_name="A", last_name="B",
            role="tashkilot_hodimi", organization=cls.org,
        )

    def _report(self, status=S.SAVED, **extra):
        return Report.objects.create(organization=self.org, statement=self.form, deadline=self.deadline,
                                     status=status, region="tashkent", **extra)


class ReportUpdateQueryTest(_Base):
    def _payload(self, n_items, with_ids=None):
        items = []
        for col in self.columns[:n_items]:
            inners = [{"value": "1"}, {"value": "2"}]
            if with_ids:
                inners = [{"id": str(i.id), "value": "9"} for i in with_ids.get(col.id, [])] or inners
            items.append({"statement_column": str(col.id), "inners": inners})
        return {"deadline": str(self.deadline.id), "report_items": items}

    def _put(self, report, payload):
        self.client.force_authenticate(self.hodim)
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.put(f"/api/v1/reports/{report.id}/update/", payload, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        return len(ctx.captured_queries), ctx.captured_queries

    def test_create_path_query_count_does_not_grow_with_items(self):
        # Ikkinchi hisobot alohida muddatda — aks holda uning PUT'i birinchisining
        # "Tashkilot Jami"sini ham o'chirib qayta yaratadi (doimiy, lekin boshqa yo'l).
        other = Deadline.objects.create(statement=self.form, submit_at="2026-04", deadline_at=timezone.localdate())
        other.organizations.add(self.org)
        r1 = self._report()
        r2 = Report.objects.create(organization=self.org, statement=self.form, deadline=other,
                                   status=S.SAVED, region="tashkent")
        n_small, _ = self._put(r1, self._payload(2))
        n_big, qs = self._put(r2, {**self._payload(8), "deadline": str(other.id)})
        self.assertEqual(ReportItemInner.objects.filter(report_item__report=r2).count(), 16)
        self.assertEqual(n_small, n_big, "\n".join(q["sql"][:110] for q in qs))

    def test_update_path_query_count_does_not_grow_with_items(self):
        r = self._report()
        self._put(r, self._payload(8))
        existing = {}
        for item in ReportItem.objects.filter(report=r).prefetch_related("inners"):
            existing[item.statement_column_id] = list(item.inners.all())
        # 2 ta ustun yangilanadi
        n_small, _ = self._put(r, self._payload(2, with_ids=existing))
        # 8 ta ustun yangilanadi
        n_big, qs = self._put(r, self._payload(8, with_ids=existing))
        self.assertEqual(n_small, n_big, "\n".join(q["sql"][:110] for q in qs))
        values = set(ReportItemInner.objects.filter(report_item__report=r).values_list("value", flat=True))
        self.assertEqual(values, {"9"})
        self.assertEqual(ReportItemInner.objects.filter(report_item__report=r).count(), 16)


class ReportSaveTest(_Base):
    def test_save_does_not_run_fk_existence_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            self._report()
        # FK mavjudligi (organization/statement/deadline/...) va pk tekshiruvi bo'lmasin;
        # unikallik cheklovi (organization_id + statement_id + deadline_id) qolishi mumkin.
        fk_checks = [q["sql"] for q in ctx.captured_queries
                     if q["sql"].startswith("SELECT 1 AS") and '"reports_report"."organization_id"' not in q["sql"]]
        self.assertEqual(fk_checks, [], "\n".join(q["sql"][:120] for q in ctx.captured_queries))

    def test_duplicate_report_is_still_rejected_by_validation(self):
        from django.core.exceptions import ValidationError
        self._report(report_season="spring")
        with self.assertRaises(ValidationError):
            self._report(report_season="spring")

    def test_status_update_skips_unique_validation(self):
        r = self._report()
        with CaptureQueriesContext(connection) as ctx:
            r.status = S.SENT
            r.save(update_fields=["status"])
        selects = [q["sql"] for q in ctx.captured_queries if q["sql"].startswith("SELECT")]
        self.assertEqual(selects, [], "\n".join(q["sql"][:120] for q in ctx.captured_queries))


class SignalScopeTest(_Base):
    def test_history_signals_listen_only_on_logged_models(self):
        self.assertFalse(post_save.has_listeners(ReportItemInner))
        self.assertFalse(post_delete.has_listeners(ReportItemInner))
        self.assertFalse(post_delete.has_listeners(ReportItem))
        self.assertTrue(post_save.has_listeners(Report))
        self.assertTrue(post_delete.has_listeners(Deadline))

    def test_history_is_still_written_for_report(self):
        from apps.logs.models import HistoryActionJournal
        r = self._report()
        r._history_user = self.hodim
        r.status = S.SENT
        r.save(update_fields=["status"])
        self.assertTrue(HistoryActionJournal.objects.filter(model_name="Report", object_id=str(r.id), action="change").exists())

    def test_report_save_does_not_query_users_for_dashboard_cache(self):
        with CaptureQueriesContext(connection) as ctx:
            self._report()
        user_queries = [q["sql"] for q in ctx.captured_queries if "users_customuser" in q["sql"]]
        self.assertEqual(user_queries, [])

    def test_dashboard_stats_refresh_after_report_change(self):
        from apps.reports.views.dashboard.dashboard_stat_service import DashboardStatService
        cache.clear()
        before = DashboardStatService(self.hodim).get_stats()["total_reports"]
        self._report()
        after = DashboardStatService(self.hodim).get_stats()["total_reports"]
        self.assertEqual(after, before + 1)


class AcceptAggregationTest(_Base):
    def test_eager_mode_builds_totals_inline(self):
        self._report(status=S.ACCEPTED)
        self.assertTrue(Report.objects.filter(statement=self.form, is_individual_general=True, organization=self.org).exists())
        self.assertTrue(Report.objects.filter(statement=self.form, is_general=True, region="tashkent").exists())
        self.assertTrue(Report.objects.filter(statement=self.form, is_republic=True).exists())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_accept_enqueues_task_after_commit(self):
        from apps.reports.tasks.aggregation import aggregate_report_totals
        with mock.patch.object(aggregate_report_totals, "delay") as delay:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                r = self._report(status=S.ACCEPTED)
                delay.assert_not_called()
            # Boshqa app'lar ham on_commit qo'shishi mumkin — hammasini bajaramiz
            self.assertGreaterEqual(len(callbacks), 1)
            for cb in callbacks:
                cb()
            delay.assert_called_once_with(str(r.id))
        self.assertFalse(Report.objects.filter(statement=self.form, is_general=True).exists())
