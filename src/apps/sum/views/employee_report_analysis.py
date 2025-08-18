from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Xodim hisobi tahlili",
    description="Xodimlar haqidagi ma’lumotlarni 4-ilova va 5-ilova kesimida yig‘ib beradi"
)
@extend_schema(tags=["Sum"])
class SumEmployeeReportAnalysisListAPIView(APIView):
    def get(self, request):
        # 4-ilova (yosh, tajriba, sertifikatlar)
        titles_1_map = {
            "30 yoshgacha bo‘lgan boshqaruv xodimlari": "30 yoshgacha bolgan xodimlar soni boshqaruv xodimlari soni",
            "40–50 yosh oralig‘idagi boshqaruv xodimlari": "40 yoshdan 50 yoshgacha bolgan boshqaruv xodimlari soni",
            "60 yoshdan yuqori boshqaruv xodimlari": "60 yoshdan yuqori bolgan boshqaruv xodimlari soni",
            "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari": "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari soni  ",
            "Tajriba – 2 yilgacha": "2 yilgacha",
            "Tajriba – 2 yildan ortiq": "2 yildan ortiq",
            "Xalqaro sertifikatli xodimlar": "Xalqaro sertifikatga ega xodimlar soni",
            "Milliy sertifikatli xodimlar": "Milliy sertifikatga ega xodimlar soni",
        }

        # 5-ilova (lavozim va mablag‘)
        titles_4_map = {
            "Tasdiqlangan shtat birligi bo‘yicha xodimlar": "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
            "Shundan xotin-qizlar": "Shundan xotin-qizlar soni",
            "Mablag‘ sarfi (mln. so‘mda)": "Mablag‘ sarfi, mln. so‘mda",
            "Dam olish/bayramda ishlaganlar": "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
            "Yuqori lavozimdagilar": "Yuqori lavozimlar",
            "Teng lavozimdagilar": "Teng lavozimlar",
            "Quyi lavozimdagilar": "Quyi lavozimlar",
        }

        # Barcha kerakli sarlavhalarni yig‘ib olish
        all_titles = list(set(titles_1_map.values()) | set(titles_4_map.values()))

        # Ma’lumotlarni yig‘ish va summalash
        items = (
            ReportItem.objects.filter(statement_column__title__in=all_titles)
            .annotate(value_as_int=Cast('value', IntegerField()))
            .values('statement_column__title')
            .annotate(total=Sum('value_as_int'))
        )

        # Natijani dict formatga o‘tkazish
        result_map = {item['statement_column__title']: item['total'] for item in items}

        # Har bir ilova bo‘yicha tartiblab qaytarish
        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map.items()}
        ilova_4 = {label: result_map.get(title, 0) for label, title in titles_4_map.items()}

        data = [{
            '4-ilova': ilova_1,
            '5-ilova': ilova_4,
        }]

        return Response(data, status=status.HTTP_200_OK)
