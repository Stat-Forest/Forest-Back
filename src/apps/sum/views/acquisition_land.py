from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Yer o‘zlashtirish",
    description="Yer o‘zlashtirish (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class SumAcquisitionLandAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # Har ikkala til uchun nomlar
        titles_map = {
            "uz": {
                "Reja": "Reja",
                "Amalda": "Amalda",
            },
            "ru": {
                "План": "Reja",
                "Фактически": "Amalda",
            }
        }


        # Baza faqat UZ sarlavhalar bo‘yicha filterlanadi
        all_titles = list(titles_map["uz"].values())

        items = (
            ReportItem.objects.filter(
                statement_column__parent__title="2025 yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
                report__statement__name="Yer o‘zlashtirish",
            )
            .annotate(value_as_int=Cast("inners__value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        # Querydan chiqqan natijani dictga o'tkazish
        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Lang bo‘yicha chiqishini ta’minlash
        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_map[lang].items()}

        data = {
            "1-ilova": ilova_1
        }

        return Response(data, status=status.HTTP_200_OK)
