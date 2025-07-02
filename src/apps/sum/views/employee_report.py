from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem, Report
from django.db.models import Sum, FloatField, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema

@extend_schema(
    summary="Xodim hisobi",
    description="Xodim hisobi statistikasi"
)

@extend_schema(tags=["Sum"])
class SumEmployeeReportListAPIView(APIView):
    def get(self, request):
        titles_map_2 = {
            "Oliy malumotli xodimlar soni ": "Oliy",
            "O'rta-maxsus malumotli xodimlar soni": "O`rta maxsus",
            "O'rta malumotli xodimlar soni ": "O`rta",
            "Jami erkaklar soni": "Erkak xodimlar",
            "Jami ayollar soni": "Ayol",
            "Jami nafaqadagi xodimlar soni": "Nafaqadagi xodimlar",
            "Ilmiy darajadagi xodimlar soni": "Ilmiy darajaga ega xodimlar",
            "Xorijiy til biladigan xodimlar soni": "Xorijiy til biladigan xodimlar",
            "Chet elda tahsil olgan yoki malaka oshirgan xodimlar": "Chet elda tashil olgan va malaka oshirgan xodimlar"
        }

        titles_map_3 = {
            "Jami yangi yaratilgan ish o'rinlar soni": "Jami yangi yaratilgan ish o'rinlar soni",
            "Doimiy ishlaydigan xodimlar soni": "Doimiy",
            "Mavsumiy ishlaydigan  xodimlar soni": "Mavsumiy",
            "Temir daftar va ayollar daftariga kiritilgan xodimlar soni": "Temir daftar va ayollar daftariga kiritilgan",
            "Kambag’al axolidan olingan": "Kambag’al axolidan olingan",
            "Kasanachilik asosida": "Kasanachilik asosida"
        }

        key_titles = {
            "Jami xodimlar soni",
            "Jami vakatlar soni",
        } | set(titles_map_2.values()) | set(titles_map_3.values())

        items = ReportItem.objects.filter(
            statement_column__title__in=key_titles
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).select_related('report', 'report__organization')

        total_employees = 0
        total_vacancies = 0
        highest_fill_percent = 0
        highest_fill_org = "UnKnown"

        most_employee = None
        most_vacancy = None

        per_report_stats = {}

        for item in items:
            title = item.statement_column.title
            report_id = item.report_id
            value = item.value_as_float or 0

            if title == "Jami xodimlar soni":
                total_employees += value
                if not most_employee or value > most_employee.value_as_float:
                    most_employee = item
            elif title == "Jami vakatlar soni":
                total_vacancies += value
                if not most_vacancy or value > most_vacancy.value_as_float:
                    most_vacancy = item

            if report_id not in per_report_stats:
                per_report_stats[report_id] = {'emp': 0, 'vac': 0, 'org': item.report.organization.name}

            if title == "Jami xodimlar soni":
                per_report_stats[report_id]['emp'] = value
            elif title == "Jami vakatlar soni":
                per_report_stats[report_id]['vac'] = value

        for stats in per_report_stats.values():
            emp = stats['emp']
            vac = stats['vac']
            if emp > 0:
                fill_percent = (vac / emp) * 100
                if fill_percent > highest_fill_percent:
                    highest_fill_percent = fill_percent
                    highest_fill_org = stats['org']

        float_sums = {
            item.statement_column.title: float(item.value_as_float or 0)
            for item in items
        }

        ilova_2 = {
            label: round(float_sums.get(title, 0), 2)
            for label, title in titles_map_2.items()
        }

        ilova_3 = {
            label: round(float_sums.get(title, 0), 2)
            for label, title in titles_map_3.items()
        }

        the_most_worker_org = getattr(most_employee.report.organization, 'name', 'UnKnown') if most_employee else 'UnKnown'
        the_most_vac_org = getattr(most_vacancy.report.organization, 'name', 'UnKnown') if most_vacancy else 'UnKnown'

        data = {
            '1-ilova': {
                "Jami xodimlar": round(total_employees, 2),
                "Eng ko'p xodimli tashkilot": the_most_worker_org,
                f"{the_most_worker_org}ning jami xodimlari": int(most_employee.value) if most_employee else 'Nomaʼlum',
                "Jami vakansiyalar": round(total_vacancies, 2),
                "Eng ko'p vakansiyali tashkilot": the_most_vac_org,
                f"{the_most_vac_org}ning jami vakansiyalari": int(most_vacancy.value) if most_vacancy else 'Nomaʼlum',
                "Umumiy to'ldirilish darajasi (%)": round((total_vacancies / total_employees) * 100, 2) if total_employees else 0,
                "Eng yuqori to'ldirilish foiziga ega tashkilot": highest_fill_org,
                "Eng yuqori to'ldirilish foizi (%)": round(highest_fill_percent, 2)
            },
            '2-ilova': ilova_2,
            '3-ilova': ilova_3
        }

        return Response(data, status=status.HTTP_200_OK)
