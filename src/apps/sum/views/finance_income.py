from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Daromad",
    description="Daromad",
    tags=["Sum"]
)
class SumFundIncomeAnalysisListAPIView(APIView):
    def get(self, request):
        titles_1_map = {
            "Ko‘chat va nihol sotish": "Ko‘chat va nihol sotish",
            "Yog‘och o‘tin sotish": "Yog‘och o‘tin sotish",
            "Sanoat, xalq iste’mol mollari": "Sanoat, xalq iste’mol mollari",
            "Aholiga pullik xizmat": "Aholiga pullik xizmat",
            "Yaylov tushumi": "Yaylov tushumi",
            "Qishloq xo‘jaligi mahsulotlari": "Qishloq xo‘jaligi mahsulotlari",
            "Chorvachilik": "Chorvachilik",
            "Parrandachilik": "Parrandachilik",
        }

        titles_4_map = {
            "Yillik reja": "Yillik reja",
            "Tushum": "Tushum",
        }

        # Barcha kerakli sarlavhalarni yig‘ib olish
        all_titles = list(set(titles_1_map.values()) | set(titles_4_map.values()))

        items = (
            ReportItem.objects.filter(
                statement_column__title__in=all_titles,
                report__status=Report.StatusChoices.ACCEPTED,
                report__is_report=True
            )
            .annotate(value_as_int=Cast("value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map.items()}
        ilova_4 = {label: result_map.get(title, 0) for label, title in titles_4_map.items()}

        data = [{
            "Daromad turlari bo‘yicha": ilova_1,
            "Tushumlar bo‘yicha": ilova_4,
        }]
        return Response(data, status=status.HTTP_200_OK)
