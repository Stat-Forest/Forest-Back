from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Urmon bilan qoplangan yerlar",
    description="Urmon bilan qoplangan yerlar"
)


@extend_schema(tags=["Sum"])
class SumCoveredForestLandAnalysisListAPIView(APIView):
    def get(self, request):
        titles_1_map = {
            "Maydoni (ga)": "Maydoni (ga)",
            "Daraxtlar zaxirasi (m³)": "Daraxtlar zaxirasi (m³)",
            "Qiymati (so‘m)": "Qiymati (so‘m)"
        }

        all_titles = list(set(titles_1_map.values()))

        items = ReportItem.objects.filter(
            statement_column__statement__name="Urmon bilan qoplangan yerlar",
            statement_column__title__in=all_titles
        ).annotate(
            value_as_int=Cast('value', IntegerField())
        ).values('statement_column__title').annotate(
            total=Sum('value_as_int')
        )

        result_map = {item['statement_column__title']: item['total'] for item in items}

        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map.items()}

        data = [{
            '2-ilova': ilova_1,
        }]

        return Response(data, status=status.HTTP_200_OK)
