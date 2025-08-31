from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Yer o‘zlashtirish",
    description="Yer o‘zlashtirish",
    tags=["Sum"]
)
class SumAcquisitionLandAnalysisListAPIView(APIView):
    def get(self, request):
        titles_map = {
            "Reja": "Reja",
            "Amalda": "Amalda",
        }

        all_titles = list(titles_map.values())

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

        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}
        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_map.items()}

        data = {
            "1-ilova": ilova_1
        }

        return Response(data, status=status.HTTP_200_OK)
