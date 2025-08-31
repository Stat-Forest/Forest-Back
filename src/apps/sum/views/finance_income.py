from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Daromad",
    description="Daromad (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class SumFundIncomeAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # Har ikkala til uchun mapping
        titles_map = {
            "uz": {
                "categories": {
                    "Ko‘chat va nihol sotish": "Ko‘chat va nihol sotish",
                    "Yog‘och o‘tin sotish": "Yog‘och o‘tin sotish",
                    "Sanoat, xalq iste’mol mollari": "Sanoat, xalq iste’mol mollari",
                    "Aholiga pullik xizmat": "Aholiga pullik xizmat",
                    "Yaylov tushumi": "Yaylov tushumi",
                    "Qishloq xo‘jaligi mahsulotlari": "Qishloq xo‘jaligi mahsulotlari",
                    "Chorvachilik": "Chorvachilik",
                    "Parrandachilik": "Parrandachilik",
                },
                "summary": {
                    "Yillik reja": "Yillik reja",
                    "Tushum": "Tushum",
                },
                "labels": {
                    "categories": "Daromad turlari bo‘yicha",
                    "summary": "Tushumlar bo‘yicha",
                }
            },
            "ru": {
                "categories": {
                    "Продажа саженцев и рассады": "Продажа саженцев и рассады",
                    "Продажа дров и древесины": "Продажа дров и древесины",
                    "Промышленные и потребительские товары": "Промышленные и потребительские товары",
                    "Платные услуги населению": "Платные услуги населению",
                    "Доход от пастбищ": "Доход от пастбищ",
                    "Сельскохозяйственная продукция": "Сельскохозяйственная продукция",
                    "Животноводство": "Животноводство",
                    "Птицеводство": "Птицеводство",
                },
                "summary": {
                    "Годовой план": "Годовой план",
                    "Доход": "Доход",
                },
                "labels": {
                    "categories": "По видам доходов",
                    "summary": "По видам поступлений",
                }
            },
        }

        # Filter uchun UZdagi titles ishlatiladi
        all_titles = list(
            set(titles_map["uz"]["categories"].values()) |
            set(titles_map["uz"]["summary"].values())
        )

        items = (
            ReportItem.objects.filter(
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .annotate(value_as_int=Cast("value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Tanlangan til bo‘yicha chiqish
        categories = {label: result_map.get(title, 0) for label, title in titles_map[lang]["categories"].items()}
        summary = {label: result_map.get(title, 0) for label, title in titles_map[lang]["summary"].items()}

        data = [{
            titles_map[lang]["labels"]["categories"]: categories,
            titles_map[lang]["labels"]["summary"]: summary,
        }]
        return Response(data, status=status.HTTP_200_OK)
