from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Sum"])
class SumEmployeeReportAnalysisListAPIView(APIView):
    def get(self, request):

        titles_1_map = {
            "30 yoshgacha bolgan xodimlar soni boshqaruv xodimlari soni": "30 yoshgacha bolgan xodimlar soni boshqaruv xodimlari soni",
            "40 yoshdan 50 yoshgacha bolgan boshqaruv xodimlari soni": "40 yoshdan 50 yoshgacha bolgan boshqaruv xodimlari soni",
            "60 yoshdan yuqori bolgan boshqaruv xodimlari soni": "60 yoshdan yuqori bolgan boshqaruv xodimlari soni",
            "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari soni  ": "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari soni  ",
            "2 yilgacha": "2 yilgacha",
            "2 yildan ortiq": "2 yildan ortiq",
            "Xalqaro sertifikatga ega xodimlar soni": "Xalqaro sertifikatga ega xodimlar soni",
            "Milliy sertifikatga ega xodimlar soni": "Milliy sertifikatga ega xodimlar soni",
        }

        titles_4_map = {
            "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni": "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
            "Shundan xotin-qizlar soni": "Shundan xotin-qizlar soni",
            "Mablag‘ sarfi, mln. so‘mda": "Mablag‘ sarfi, mln. so‘mda",
            "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni": "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
            "Yuqori lavozimlar": "Yuqori lavozimlar",
            "Teng lavozimlar": "Teng lavozimlar",
            "Quyi lavozimlar": "Quyi lavozimlar",
        }

        all_titles = list(set(titles_1_map.values()) | set(titles_4_map.values()))

        items = ReportItem.objects.filter(statement_column__title__in=all_titles).annotate(
            value_as_int=Cast('value', IntegerField())
        ).values('statement_column__title').annotate(
            total=Sum('value_as_int')
        )

        result_map = {item['statement_column__title']: item['total'] for item in items}

        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map.items()}
        ilova_4 = {label: result_map.get(title, 0) for label, title in titles_4_map.items()}

        data = {
            '1-ilova': ilova_1,
            '4-ilova': ilova_4,
        }

        return Response(data, status=status.HTTP_200_OK)
