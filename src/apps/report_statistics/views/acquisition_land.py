from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem

@extend_schema(
    summary="Yer o'zlashtirish",
    description="Yer o'zlashtirish"
)

@extend_schema(tags=["Statistics"])
class StatisticsLandAcquisitionAPIView(APIView):
    def get(self, request):
        titles_ilova_1 = [
            "Reja",
            "Amalda",
            "1-chorak",
            "2-chorak",
            "3-chorak",
            "4-chorak",
        ]

        all_titles = titles_ilova_1

        qs = ReportItem.objects.filter(
            statement_column__statement__name="Yer o'zlashtirish",
            statement_column__title__in=all_titles
        ).annotate(
            numeric_value=Cast('value', FloatField())
        ).values(
            'report__organization__region',
            'statement_column__title'
        ).annotate(
            total=Sum('numeric_value')
        )

        grouped_data = defaultdict(lambda: defaultdict(float))
        for item in qs:
            region = item['report__organization__region']
            title = item['statement_column__title']
            total = item['total'] or 0
            grouped_data[region][title] = total

        data = [{
            "1-ilova": [],
        }]

        for region in RegionChoices.values:
            data[0]["1-ilova"].append({
                'name': region,
                **{title: grouped_data[region].get(title, 0) for title in titles_ilova_1}
            })


        return Response(data, status=HTTP_200_OK)
