"""
Hisobotlar ro'yxati: item/qiymatlar model obyektlari o'rniga yengil lug'atlar
bilan yuklanadi (300 hisobot x 120 ustun uchun 4.8 s -> ~1 s), natija eski
(prefetch) yo'l bilan bir xil.
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.general.models import Organization
from apps.reports.models import Deadline, Report, ReportItem, ReportItemInner, Statement, StatementColumn
from apps.reports.serializers.reports import ReportListSerializer

User = get_user_model()
URL = "/api/v1/reports/"


class ReportListItemsTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        dept = Statement.objects.create(name="Bo'lim L", name_uz="Bo'lim L", name_ru="Отдел L")
        cls.form = Statement.objects.create(name="Shakl L", name_uz="Shakl L", name_ru="Форма L", parent=dept)
        top = StatementColumn.objects.create(statement=cls.form, title="1-ilova", title_uz="1-ilova", title_ru="1-прил", ordering="1", is_user_input=False)
        cls.c_org = StatementColumn.objects.create(statement=cls.form, parent=top, title="Tashkilot nomi", title_uz="Tashkilot nomi", title_ru="Наименование организации", ordering="1.1", is_organization=True)
        cls.c_val = StatementColumn.objects.create(statement=cls.form, parent=top, title="Maydon", title_uz="Maydon", title_ru="Площадь", ordering="1.2")
        cls.c_10 = StatementColumn.objects.create(statement=cls.form, title="10-ilova", title_uz="10-ilova", title_ru="10-прил", ordering="10")
        cls.orgs = [Organization.objects.create(name=f"Org L{i}", name_uz=f"Org L{i}", name_ru=f"Орг L{i}", region="tashkent") for i in range(2)]
        cls.deadline = Deadline.objects.create(statement=cls.form, submit_at="2026-06", deadline_at=timezone.localdate())
        cls.deadline.organizations.add(*cls.orgs)
        cls.reports = []
        for org in cls.orgs:
            r = Report.objects.create(organization=org, statement=cls.form, deadline=cls.deadline, status="saved", region="tashkent")
            for col, values in ((cls.c_10, ["7"]), (cls.c_val, ["12.5", "3"]), (cls.c_org, ["x"])):
                item = ReportItem.objects.create(report=r, statement_column=col)
                for v in values:
                    ReportItemInner.objects.create(report_item=item, value=v)
            cls.reports.append(r)
        cls.root = User.objects.create_superuser(email="root_l@example.com", password="x", first_name="R", last_name="T")

    def _get(self, **params):
        self.client.force_authenticate(self.root)
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.get(URL, {"statement": str(self.form.id), "per_page": 20, **params})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json(), ctx.captured_queries

    def test_items_equal_prefetch_path_and_are_ordered(self):
        data, _ = self._get()
        rows = {row["id"]: row for row in data["results"]}
        for report in self.reports:
            api_items = rows[str(report.id)]["report_items"]
            # eski yo'l: prefetch obyektlari bilan, items_by_report'siz
            prefetched = Report.objects.prefetch_related("report_items__statement_column__parent", "report_items__inners", "signatures").get(pk=report.pk)
            ref = ReportListSerializer(prefetched, context={"lang": "uz"}).data["report_items"]
            self.assertEqual(api_items, ref)
            cols = api_items[0]["statement_columns"]
            self.assertEqual([c["statement_column_name"] for c in cols], ["1-ilova – Tashkilot nomi", "1-ilova – Maydon", "10-ilova"])
            self.assertEqual([i["value"] for i in cols[1]["inners"]], ["12.5", "3"])
            self.assertEqual(cols[0]["inners"][0]["value"], report.organization.name)  # tashkilot nomi almashtiriladi

    def test_items_are_loaded_as_values_only_for_the_page(self):
        data, queries = self._get(per_page=1)
        self.assertEqual(len(data["results"]), 1)
        item_queries = [q["sql"] for q in queries if 'FROM "reports_reportitem"' in q["sql"]]
        self.assertTrue(item_queries)
        for sql in item_queries:
            self.assertNotIn('"reports_statementcolumn"', sql, "item'lar ustun bilan JOIN qilinmasligi kerak")
            self.assertNotIn('"reports_reportitem"."created_by_id"', sql, "faqat kerakli maydonlar (values)")
            self.assertEqual(sql.count("::uuid"), 1, "faqat sahifadagi hisobot uchun")
