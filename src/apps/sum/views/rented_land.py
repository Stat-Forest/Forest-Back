from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Ijaraga berilgan yerlar hisobi",
    description="Ijaraga berilgan yerlar hisobi (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class SumRentedAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # Har ikkala til uchun mapping
        titles_map = {
            "uz": {
                "Jami ijara yer maydoni (ga)": "Jami ijara yer maydoni (ga)",
                "Yangi yaratilgan ish o‘rinlari soni": "Yangi yaratilgan ish o‘rinlari soni",
                "Kiritiladigan investitsiya qiymati (ming so‘m)": "Kiritiladigan investitsiya qiymati (ming so‘m)",
            },
            "ru": {
                "Общая площадь арендованных земель (га)": "Jami ijara yer maydoni (ga)",
                "Количество вновь созданных рабочих мест": "Yangi yaratilgan ish o‘rinlari soni",
                "Объем инвестиций (тыс. сум)": "Kiritiladigan investitsiya qiymati (ming so‘m)",
            },
        }

        # Bazada faqat UZ nomlari bo‘yicha qidiriladi
        all_titles = list(titles_map["uz"].values())

        items = (
            ReportItem.objects.filter(
                statement_column__statement__name="Ijaraga berilgan yerlar hisobi",
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .annotate(value_as_int=Cast("inners__value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Foydalanuvchining tanlagan tiliga qarab chiqish
        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_map[lang].items()}

        data = {
            "1-ilova": ilova_1
        }

        return Response(data, status=status.HTTP_200_OK)
