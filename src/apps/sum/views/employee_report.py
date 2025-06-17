from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem, Report
from django.db.models import Sum, FloatField,IntegerField
from django.db.models.functions import Cast


class SumEmployeeReportListAPIView(APIView):
    def get(self, request):
        employee_item = ReportItem.objects.filter(
            statement_column__title='Jami xodimlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).order_by('-value_as_float').first()
        rep_1 = employee_item.report if employee_item else None

        vacancy_item = ReportItem.objects.filter(
            statement_column__title='Jami vakatlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).order_by('-value_as_float').first()
        rep_2 = vacancy_item.report if vacancy_item else None

        total_employees = ReportItem.objects.filter(
            statement_column__title='Jami xodimlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).aggregate(sum_value=Sum('value_as_float'))['sum_value'] or 0

        total_vacancies = ReportItem.objects.filter(
            statement_column__title='Jami vakatlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).aggregate(sum_value=Sum('value_as_float'))['sum_value'] or 0

        highest_fill_percent = 0
        highest_fill_org = "UnKnown"

        all_reports = Report.objects.all()
        for report in all_reports:
            emp_item = report.report_items.filter(statement_column__title='Jami xodimlar soni').first()
            vac_item = report.report_items.filter(statement_column__title='Jami vakatlar soni').first()

            try:
                emp_value = float(emp_item.value) if emp_item and emp_item.value else 0
                vac_value = float(vac_item.value) if vac_item and vac_item.value else 0

                if emp_value > 0:
                    fill_percent = (vac_value / emp_value) * 100
                    if fill_percent > highest_fill_percent:
                        highest_fill_percent = fill_percent
                        highest_fill_org = report.organization.name
            except ValueError:
                continue

        the_most_worker_org = getattr(rep_1.organization, 'name', 'UnKnown') if rep_1 else 'UnKnown'
        the_most_vac_org = getattr(rep_2.organization, 'name', 'UnKnown') if rep_2 else 'UnKnown'

        titles_map_2 = {
            "Oliy malumotli xodimlar soni": "Oliy",
            "O'rta-maxsus malumotli xodimlar soni": "O`rta maxsus",
            "O'rta malumotli xodimlar soni": "O`rta",
            "Jami erkaklar soni": "Erkak xodimlar",
            "Jami ayollar soni": "Ayol",
            "Jami nafaqadagi xodimlar soni": "Nafaqadagi xodimlar",
            "Ilmiy darajadagi xodimlar soni": "Ilmiy darajaga ega xodimlar",
            "Xorijiy til biladigan xodimlar soni": "Xorijiy til biladigan xodimlar",
            "Chet elda tahsil olgan yoki malaka oshirgan xodimlar": "Chet elda tashil olgan va malaka oshirgan xodimlar"
        }

        ilova_2 = {}
        for label, title in titles_map_2.items():
            item = ReportItem.objects.filter(statement_column__title=title).annotate(
                value_as_float=Cast('value', IntegerField())
            ).aggregate(total=Sum('value_as_float'))
            ilova_2[label] = item['total'] or 0

        titles_map_3 = {
            "Jami yangi yaratilgan ish o'rinlar soni": "Jami yangi yaratilgan ish o'rinlar soni",
            "Doimiy ishlaydigan xodimlar soni": "Doimiy",
            "Mavsumiy ishlaydigan  xodimlar soni": "Mavsumiy",
            "Temir daftar va ayollar daftariga kiritilgan xodimlar soni": "Temir daftar va ayollar daftariga kiritilgan",
            "Kambag’al axolidan olingan": "Kambag’al axolidan olingan",
            "Kasanachilik asosida": "Kasanachilik asosida"
        }

        ilova_3 = {}
        for label, title in titles_map_3.items():
            count = ReportItem.objects.filter(statement_column__title=title).count()
            ilova_3[label] = count

        data = {
            '1-ilova': {
                "Jami xodimlar": total_employees,
                "Eng ko'p xodimli tashkilot": the_most_worker_org,
                f"{the_most_worker_org}ning jami xodimlari": employee_item.value if employee_item else 'Nomaʼlum',
                "Jami vakansiyalar": total_vacancies,
                "Eng ko'p vakansiyali tashkilot": the_most_vac_org,
                f"{the_most_vac_org}ning jami vakansiyalari": vacancy_item.value if vacancy_item else 'Nomaʼlum',
                "Umumiy to'ldirilish darajasi (%)": round((total_vacancies / total_employees) * 100, 2) if total_employees else 0,
                "Eng yuqori to'ldirilish foiziga ega tashkilot": highest_fill_org,
                "Eng yuqori to'ldirilish foizi (%)": round(highest_fill_percent, 2)
            },
            '2-ilova': ilova_2,
            '3-ilova': ilova_3
        }

        return Response(data, status=status.HTTP_200_OK)
