from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import FloatField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Xodim hisobi",
    description="Xodim hisobi statistikasi",
    tags=["Sum"]
)
class SumEmployeeReportListAPIView(APIView):

    @staticmethod
    def get_org_name(report):
        """Tashkilot nomini xavfsiz qaytaradi"""
        return report.organization.name if report and report.organization else "Nomaʼlum"

    def get(self, request):
        # === Column mapping ===
        titles_map_2 = {
            "Oliy malumotli xodimlar soni": "Oliy",
            "O'rta-maxsus malumotli xodimlar soni": "O`rta maxsus",
            "O'rta malumotli xodimlar soni": "O`rta",
            "Jami erkaklar soni": "Erkak xodimlar",
            "Jami ayollar soni": "Ayol",
            "Jami nafaqadagi xodimlar soni": "Nafaqadagi xodimlar",
            "Ilmiy darajadagi xodimlar soni": "Ilmiy darajaga ega xodimlar",
            "Xorijiy til biladigan xodimlar soni": "Xorijiy til biladigan xodimlar",
            "Chet elda tahsil olgan yoki malaka oshirgan xodimlar": "Chet elda malaka oshirganlar",
        }

        titles_map_3 = {
            "Jami yangi yaratilgan ish o'rinlar soni": "Jami yangi ish o‘rinlari",
            "Doimiy ishlaydigan xodimlar soni": "Doimiy",
            "Mavsumiy ishlaydigan xodimlar soni": "Mavsumiy",
            "Temir daftar va ayollar daftariga kiritilgan xodimlar soni": "Temir daftar/ayollar daftaridagi",
            "Kambag’al axolidan olingan": "Kambag’al axolidan olingan",
            "Kasanachilik asosida": "Kasanachilik asosida",
        }

        key_titles = {
            "Jami xodimlar soni",
            "Jami vakatlar soni",
            *titles_map_2.keys(),
            *titles_map_3.keys(),
        }

        # === Query ===
        items = (
            ReportItem.objects.filter(statement_column__title__in=key_titles)
            .annotate(value_as_float=Cast("value", FloatField()))
            .select_related("report", "report__organization", "statement_column")
        )

        # === Totals ===
        totals = {}
        for item in items:
            title = item.statement_column.title.strip()
            totals[title] = totals.get(title, 0) + (item.value_as_float or 0)

        total_employees = totals.get("Jami xodimlar soni", 0)
        total_vacancies = totals.get("Jami vakatlar soni", 0)

        # === Most employee / vacancy org ===
        most_employee = max(
            (i for i in items if i.statement_column.title.strip() == "Jami xodimlar soni"),
            key=lambda x: x.value_as_float or 0,
            default=None,
        )
        most_vacancy = max(
            (i for i in items if i.statement_column.title.strip() == "Jami vakatlar soni"),
            key=lambda x: x.value_as_float or 0,
            default=None,
        )

        the_most_worker_org = self.get_org_name(most_employee.report) if most_employee else "Nomaʼlum"
        the_most_vac_org = self.get_org_name(most_vacancy.report) if most_vacancy else "Nomaʼlum"

        # === Per-report stats ===
        per_report_stats = {}
        for item in items:
            rid = item.report_id
            if rid not in per_report_stats:
                per_report_stats[rid] = {"emp": 0, "vac": 0, "org": self.get_org_name(item.report)}

            title = item.statement_column.title.strip()
            if title == "Jami xodimlar soni":
                per_report_stats[rid]["emp"] = item.value_as_float or 0
            elif title == "Jami vakatlar soni":
                per_report_stats[rid]["vac"] = item.value_as_float or 0

        # === Highest fill percent ===
        highest_fill_percent, highest_fill_org = 0, "Nomaʼlum"
        for stats in per_report_stats.values():
            emp, vac = stats["emp"], stats["vac"]
            if emp + vac > 0:
                fill_percent = (emp / (emp + vac)) * 100
                if fill_percent > highest_fill_percent:
                    highest_fill_percent, highest_fill_org = fill_percent, stats["org"]

        # === Ilova-2 & Ilova-3 ===
        ilova_2 = {label: round(totals.get(title, 0), 2) for title, label in titles_map_2.items()}
        ilova_3 = {label: round(totals.get(title, 0), 2) for title, label in titles_map_3.items()}

        # === Response ===
        data = [{
            "1-ilova": {
                "Jami xodimlar": round(total_employees, 2),
                "Eng ko'p xodimli tashkilot": the_most_worker_org,
                f"{the_most_worker_org} jami xodimlari": int(most_employee.value) if most_employee else 0,
                "Jami vakansiyalar": round(total_vacancies, 2),
                "Eng ko'p vakansiyali tashkilot": the_most_vac_org,
                f"{the_most_vac_org} jami vakansiyalari": int(most_vacancy.value) if most_vacancy else 0,
                "Umumiy to'ldirilish darajasi (%)": round(
                    (total_employees / (total_employees + total_vacancies)) * 100, 2
                ) if (total_employees + total_vacancies) else 0,
                "Eng yuqori to'ldirilish foiziga ega tashkilot": highest_fill_org,
                "Eng yuqori to'ldirilish foizi (%)": round(highest_fill_percent, 2),
            },
            "2-ilova": ilova_2,
            "3-ilova": ilova_3,
        }]

        return Response(data, status=status.HTTP_200_OK)
