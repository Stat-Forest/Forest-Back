from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Jamg'arma",
    description="Jamg'arma"
)

@extend_schema(tags=["Sum"])
class SumFundAnalysisListAPIView(APIView):
    def get(self, request):
        titles_1_map = {
            "Ruxsatnoma olish uchun arizalarni ko‘rib chiqganlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (1001)": "Jami tushum",
            "Hayvonot va o‘simlik dunyosiga yetkazilgan zarar o‘rnini qoplash bo‘yicha undirilgan mablag‘ (1007)": "Jami tushum",
            "Ruxsat etilgan hududlarda ovchilik qilish uchun tushgan mablag‘ (50%)": "Jami tushum",
            "Ummon fondi yerlaridagi boyliklar va madaniy meroslardan foydalanishdan tushgan mablag‘ (100%)": "Jami tushum",
            "Ummon xo‘jaligi yog‘och kesishdan tushgan mablag‘ (50%)": "Jami tushum",
            "Boshqa daromadlar (101)": "Jami tushum",
        }


        all_titles_labels = list(set(titles_1_map.keys()))
        all_titles = list(set(titles_1_map.values()))

        items = ReportItem.objects.filter(
            statement_column__parent__title__in=all_titles_labels,
            statement_column__title__in=all_titles
        ).annotate(
            value_as_int=Cast('value', IntegerField())
        ).values('statement_column__title').annotate(
            total=Sum('value_as_int')
        )

        result_map = {item['statement_column__title']: item['total'] for item in items}

        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map.items()}

        data = {
            'Jamg\'arma': ilova_1,
        }

        return Response(data, status=status.HTTP_200_OK)
