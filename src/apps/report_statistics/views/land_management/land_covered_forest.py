from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem


FIELD_NAMES = {
    "uz": {"region": "Hudud", "forest_land": "Urmon bilan qoplangan yerlar"},
    "ru": {"region": "Регион", "forest_land": "Urmon bilan qoplangan yerlar"},  # RU da ham o‘zbekcha qoladi
}

REGION_LABELS = {
    "tashkent": {"uz": "Toshkent", "ru": "Ташкент"},
    "namangan": {"uz": "Namangan", "ru": "Наманган"},
    "andijon": {"uz": "Andijon", "ru": "Андижан"},
    "fargona": {"uz": "Farg‘ona", "ru": "Фергана"},
    "buxoro": {"uz": "Buxoro", "ru": "Бухара"},
    "samarqand": {"uz": "Samarqand", "ru": "Самарканд"},
    "navoiy": {"uz": "Navoiy", "ru": "Навои"},
    "qashqadaryo": {"uz": "Qashqadaryo", "ru": "Кашкадарья"},
    "surxondaryo": {"uz": "Surxondaryo", "ru": "Сурхандарья"},
    "xorazm": {"uz": "Xorazm", "ru": "Хорезм"},
    "sirdaryo": {"uz": "Sirdaryo", "ru": "Сырдарья"},
    "jizzax": {"uz": "Jizzax", "ru": "Джизак"},
    "qoraqalpogiston": {"uz": "Qoraqalpog‘iston", "ru": "Каракалпакстан"},
    "republic": {"uz": "Respublika tashkilotlari", "ru": "Республиканские организации"},
}


@extend_schema(
    summary="Urmon bilan qoplangan yerlar",
    description="Urmon bilan qoplangan yerlar (UZ va RU tillarini qo‘llab-quvvatlaydi)",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatisticsForestLandAPIView(APIView):
    def get_translated_titles(self, lang):
        return [
            ("Maydoni (ga)", "Площадь (га)"),
            ("Daraxtlar zaxirasi (m³)", "Запасы древесины (м³)"),
            ("Qiymati (so‘m)", "Стоимость (сум)"),
        ]

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        field_names = FIELD_NAMES[lang]
        titles = self.get_translated_titles(lang)

        all_titles = [uz if lang == "uz" else ru for uz, ru in titles]
        title_key = "statement_column__title" if lang == "uz" else "statement_column__title_ru"

        qs = (
            ReportItem.objects.filter(
                statement_column__statement__name="Urmon bilan qoplangan yerlar",
                **{f"{title_key}__in": all_titles},
                report__is_report=True,
            )
            .annotate(numeric_value=Cast("value", FloatField()))
            .values("report__organization__region", title_key)
            .annotate(total=Sum("numeric_value"))
        )

        grouped_data = defaultdict(lambda: defaultdict(float))
        for item in qs:
            region = item["report__organization__region"]
            title = item[title_key]
            grouped_data[region][title] = item["total"] or 0

        data = [{field_names["forest_land"]: []}]

        for region_key, _ in RegionChoices.choices:
            region_name = REGION_LABELS.get(region_key, {}).get(lang, region_key)

            data[0][field_names["forest_land"]].append(
                {
                    field_names["region"]: region_name,
                    **{
                        (ru if lang == "ru" else uz): grouped_data[region_key].get(
                            (ru if lang == "ru" else uz), 0
                        )
                        for uz, ru in titles
                    },
                }
            )

        return Response(data, status=HTTP_200_OK)
