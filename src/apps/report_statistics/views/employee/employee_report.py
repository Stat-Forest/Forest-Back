from collections import defaultdict

from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from django.utils import translation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report


FIELD_NAMES = {
    "uz": {
        "region": "hudud",
        "ilova1": "1-ilova",
        "ilova2": "2-ilova",
        "ilova3": "3-ilova",
    },
    "ru": {
        "region": "регион",
        "ilova1": "1-ilova",
        "ilova2": "2-ilova",
        "ilova3": "3-ilova",
    },
}


@extend_schema(
    summary="Xodim hisobi",
    description="Xodim hisobi (UZ va RU tillarini qo‘llab-quvvatlaydi)",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="deadline",
            description="Deadline ID bo‘yicha filter",
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class StatisticsEmployeeReportAPIView(APIView):

    def get_translated_titles(self, lang: str) -> dict:
        return {
            "uz": {
                "1": [
                    "Boshqaruv xodimlari",
                    "Mutaxassislar",
                    "Ishlab chiqarish xodimlari",
                    "Texnik hodim",
                    "Xizmat korsatuvchi xodimlar",
                    "ishchilar",
                ],
                "2": [
                    "Oliy",
                    "O`rta-mahsus",
                    "O'rta-maxsus",
                ],
                "3": [
                    "Doimiy",
                    "Mavsumiy",
                ],
            },
            "ru": {
                "1": [
                    "Руководящие работники",
                    "Специалисты",
                    "Производственные работники",
                    "Технический персонал",
                    "Обслуживающий персонал",
                    "Рабочие",
                ],
                "2": [
                    "Высшее",
                    "Среднее специальное",
                    "Среднее",
                ],
                "3": [
                    "Постоянные",
                    "Сезонные",
                ],
            },
        }[lang]

    def get_aggregated_data_by_titles(
        self,
        titles,
        lang,
        parent_title=None,
        deadline_id=None,
    ):
        title_key = (
            "statement_column__title"
            if lang == "uz"
            else "statement_column__title_ru"
        )
        parent_key = (
            "statement_column__parent__title"
            if lang == "uz"
            else "statement_column__parent__title_ru"
        )

        filters = {
            f"{title_key}__in": titles,
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
        }

        if parent_title:
            filters[parent_key] = parent_title

        if deadline_id:
            filters["report__deadline_id"] = deadline_id

        return (
            ReportItem.objects.filter(**filters)
            .values("report__organization__region", title_key)
            .annotate(
                total=Sum(Cast("inners__value", FloatField()))
            )
        )

    def get(self, request):
        # --- params ---
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)

        translated_titles = self.get_translated_titles(lang)
        parent_title_ilova_1 = "xodimlardan" if lang == "uz" else "из них"

        qs1 = self.get_aggregated_data_by_titles(
            translated_titles["1"],
            lang,
            parent_title=parent_title_ilova_1,
            deadline_id=deadline_id,
        )
        qs2 = self.get_aggregated_data_by_titles(
            translated_titles["2"],
            lang,
            deadline_id=deadline_id,
        )
        qs3 = self.get_aggregated_data_by_titles(
            translated_titles["3"],
            lang,
            deadline_id=deadline_id,
        )

        title_key = (
            "statement_column__title"
            if lang == "uz"
            else "statement_column__title_ru"
        )

        grouped_data = defaultdict(lambda: defaultdict(float))

        for qs in (qs1, qs2, qs3):
            for item in qs:
                region = item["report__organization__region"]
                title = item[title_key]
                grouped_data[region][title] += item["total"] or 0

        field_names = FIELD_NAMES[lang]

        data = [{
            field_names["ilova1"]: [],
            field_names["ilova2"]: [],
            field_names["ilova3"]: [],
        }]

        for region_key, region_label in RegionChoices.choices:
            region_name = str(region_label)

            data[0][field_names["ilova1"]].append({
                field_names["region"]: region_name,
                **{
                    title: grouped_data[region_key].get(title, 0)
                    for title in translated_titles["1"]
                },
            })

            data[0][field_names["ilova2"]].append({
                field_names["region"]: region_name,
                **{
                    title: grouped_data[region_key].get(title, 0)
                    for title in translated_titles["2"]
                },
            })

            data[0][field_names["ilova3"]].append({
                field_names["region"]: region_name,
                **{
                    title: grouped_data[region_key].get(title, 0)
                    for title in translated_titles["3"]
                },
            })

        return Response(data, status=HTTP_200_OK)
