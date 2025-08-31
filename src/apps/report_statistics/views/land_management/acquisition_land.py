from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem

from apps.reports.models import Report


FIELD_NAMES = {
    "uz": {
        "region": "Hudud",
        "by_income_types": "Yer o‘zlashtirish",
    },
    "ru": {
        "region": "Регион",
        "by_income_types": "Yer o‘zlashtirish",
    },
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
    summary="Yer o‘zlashtirish",
    description="Yer o‘zlashtirish (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class StatisticsFinanceIncomeAPIView(APIView):
    def get_translated_titles(self):
        return {
            "by_income_types": [
                ("Reja", "План"),
                ("Amalda", "Фактически")
            ]
        }

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        field_names = FIELD_NAMES[lang]
        translated = self.get_translated_titles()

        # Queryga kerakli title-lar
        all_titles = [
            (uz if lang == "uz" else ru)
            for section in translated.values()
            for uz, ru in section
        ]

        title_key = "statement_column__title" if lang == "uz" else "statement_column__title_ru"

        # 🔑 accepted status bo'yicha filter qo'shildi
        qs = (
            ReportItem.objects.filter(
                **{f"{title_key}__in": all_titles},
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
                report__statement__name='Yer o‘zlashtirish',
            )
            .values("report__organization__region", title_key)
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        # Natijalarni region va title bo‘yicha guruhlash
        grouped_data = defaultdict(lambda: defaultdict(float))
        for item in qs:
            region = item["report__organization__region"]
            title = item[title_key]
            grouped_data[region][title] = item["total"] or 0

        # Response data
        data = [{field_names["by_income_types"]: []}]

        for region_key, _ in RegionChoices.choices:
            region_name = REGION_LABELS.get(region_key, {}).get(lang, region_key)

            for section_key in ["by_income_types"]:
                data[0][field_names[section_key]].append(
                    {
                        field_names["region"]: region_name,
                        **{
                            (ru if lang == "ru" else uz): grouped_data[region_key].get(
                                (ru if lang == "ru" else uz), 0
                            )
                            for uz, ru in translated[section_key]
                        },
                    }
                )

        return Response(data, status=HTTP_200_OK)
