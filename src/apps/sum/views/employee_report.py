from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast

from apps.reports.models import ReportItem

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

@extend_schema(
    summary="Xodim hisobi",
    description="Xodim hisobi statistikasi (1-ilova, 2-ilova, 3-ilova)",
    tags=["Sum"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        )
    ]
)
class SumEmployeeReportListAPIView(APIView):

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        titles_map_2 = {
            "uz": {
                "Oliy": "Oliy",
                "O`rta-mahsus": "O`rta-mahsus",
                "O'rta-maxsus": "O'rta-maxsus",
                "Ayol": "Ayol",
                "Erkak xodimlar": "Erkak xodimlar",
                "Nafaqadagi xodimlar": "Nafaqadagi xodimlar",
                "Ilmiy darajaga ega xodimlar": "Ilmiy darajaga ega xodimlar",
                "Xorijiy til biladigan xodimlar": "Xorijiy til biladigan xodimlar",
                "Chet elda tahsil olgan va malaka oshirgan xodimlar": "Chet elda tahsil olgan va malaka oshirgan xodimlar"
            },
            "ru": {
                "Высшее": "Oliy",
                "Среднее специальное": "O`rta-mahsus",
                "Среднее": "O'rta-maxsus",
                "Женщины": "Ayol",
                "Мужчины": "Erkak xodimlar",
                "Пенсионеры": "Nafaqadagi xodimlar",
                "С ученой степенью": "Ilmiy darajaga ega xodimlar",
                "Знающие иностранные языки": "Xorijiy til biladigan xodimlar",
                "Обучавшиеся или проходившие стажировку за рубежом": "Chet elda tahsil olgan va malaka oshirgan xodimlar"
            }
        }

        titles_map_3 = {
            "uz": {
                "Jami yangi yaratilgan ish o'rinlar soni": "Jami yangi yaratilgan ish o'rinlar soni",
                "Doimiy": "Doimiy",
                "Mavsumiy": "Mavsumiy",
                "Temir daftar va ayollar daftariga kiritilgan": "Temir daftar va ayollar daftariga kiritilgan",
                "Kambag’al axolidan olingan": "Kambag’al axolidan olingan",
                "Kasanachilik asosida": "Kasanachilik asosida"
            },
            "ru": {
                "Всего новых рабочих мест": "Jami yangi yaratilgan ish o'rinlar soni",
                "Постоянные": "Doimiy",
                "Сезонные": "Mavsumiy",
                "Включённые в железную и женскую книги": "Temir daftar va ayollar daftariga kiritilgan",
                "Из числа малообеспеченных": "Kambag’al axolidan olingan",
                "На основе надомного труда": "Kasanachilik asosida"
            }
        }

        key_titles = {"Jami xodimlar soni", "Jami vakatlar soni"} \
                     | set(titles_map_2["uz"].values()) \
                     | set(titles_map_3["uz"].values())

        items = (
            ReportItem.objects.filter(statement_column__title__in=key_titles)
            .values("report_id", "report__organization__name", "statement_column__title")
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        totals = {}
        per_report_stats = {}
        for item in items:
            title = item["statement_column__title"]
            org_name = item["report__organization__name"]
            rid = item["report_id"]
            total_val = item["total"] or 0

            totals[title] = totals.get(title, 0) + total_val

            if rid not in per_report_stats:
                per_report_stats[rid] = {"emp": 0, "vac": 0, "org": org_name}
            if title == "Jami xodimlar soni":
                per_report_stats[rid]["emp"] = total_val
            elif title == "Jami vakatlar soni":
                per_report_stats[rid]["vac"] = total_val

        total_employees = totals.get("Jami xodimlar soni", 0)
        total_vacancies = totals.get("Jami vakatlar soni", 0)

        most_employee = max(per_report_stats.values(), key=lambda x: x["emp"], default=None)
        most_vacancy = max(per_report_stats.values(), key=lambda x: x["vac"], default=None)

        the_most_worker_org = most_employee["org"] if most_employee else "Nomaʼlum"
        the_most_vac_org = most_vacancy["org"] if most_vacancy else "Nomaʼlum"

        highest_fill_percent = 0
        highest_fill_org = "Nomaʼlum"
        for stats in per_report_stats.values():
            emp, vac = stats["emp"], stats["vac"]
            if emp + vac > 0:
                fill_percent = (emp / (emp + vac)) * 100
                if fill_percent > highest_fill_percent:
                    highest_fill_percent = fill_percent
                    highest_fill_org = stats["org"]

        # 2-ilova va 3-ilova keylari faqat lang bo‘yicha chiqadi
        ilova_2 = {
            label: round(totals.get(title, 0), 2)
            for label, title in titles_map_2[lang].items()
        }
        ilova_3 = {
            label: round(totals.get(title, 0), 2)
            for label, title in titles_map_3[lang].items()
        }

        data = [
            {
                "1-ilova": {
                    "Jami xodimlar" if lang == "uz" else "Всего сотрудников": round(total_employees, 2),
                    "Jami vakansiyalar" if lang == "uz" else "Всего вакансий": round(total_vacancies, 2),
                    "Umumiy to'ldirilish darajasi (%)" if lang == "uz" else "Общий уровень заполненности (%)": round(
                        (total_employees / (total_employees + total_vacancies)) * 100, 2
                    ) if (total_employees + total_vacancies) else 0,
                    "Eng yuqori to'ldirilish foiziga ega tashkilot" if lang == "uz" else "Организация с самым высоким уровнем заполненности": highest_fill_org,
                    "Eng yuqori to'ldirilish foizi (%)" if lang == "uz" else "Максимальный процент заполненности (%)": round(highest_fill_percent, 2),
                },
                "2-ilova": ilova_2,
                "3-ilova": ilova_3,
            }
        ]

        return Response(data, status=status.HTTP_200_OK)
