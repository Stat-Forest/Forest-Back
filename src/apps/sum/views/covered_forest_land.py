from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem, Report
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


@extend_schema(
    summary="Urmon bilan qoplangan yerlar",
    description="Urmon bilan qoplangan yerlar (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class SumCoveredForestLandAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # Har ikkala til uchun nomlar
        titles_map = {
            "uz": {
                "Maydoni (ga)": "Maydoni (ga)",
                "Daraxtlar zaxirasi (m³)": "Daraxtlar zaxirasi (m³)",
                "Qiymati (so‘m)": "Qiymati (so‘m)",
            },
            "ru": {
                "Площадь (га)": "Maydoni (ga)",
                "Запасы деревьев (м³)": "Daraxtlar zaxirasi (m³)",
                "Стоимость (сум)": "Qiymati (so‘m)",
            },
        }

        # Filter qilish uchun bazadagi UZ nomlari ishlatiladi
        all_titles = list(titles_map["uz"].values())

        items = (
            ReportItem.objects.filter(
                statement_column__statement__name="Urmon bilan qoplangan yerlar",
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .annotate(value_as_int=Cast("inners__value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        # Natijani dict formatga o‘tkazish
        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Lang bo‘yicha chiqishini ta’minlash
        ilova_2 = {label: result_map.get(title, 0) for label, title in titles_map[lang].items()}

        data = {
            "2-ilova": ilova_2
        }

        return Response(data, status=status.HTTP_200_OK)
