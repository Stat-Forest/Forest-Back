from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Jamg'arma",
    description="Jamg'arma (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class SumFundAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # Har ikkala til uchun mapping
        titles_map = {
            "uz": {
                "Ruxsatnoma olish uchun arizalarni ko‘rib chiqqanlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (100%)": "Jami tushum",
                "Hayvonot va o‘simlik dunyosiga yetkazilgan zararni qoplash bo‘yicha undirilgan mablag‘ (100%)": "Jami tushum",
                "Ruxsat etilgan hududlarda chorva boqish, pichan o‘rish, asalarilar uyasi va qutilarini joylashtirish, daraxt kesmagan holda o‘tin yig‘ish va boshqa maqsadlardan tushgan mablag‘ (50%)": "Jami tushum",
                "O‘rmon fondi yerlaridagi bog‘lar va madaniy o‘rmonzorlani fuqarolarga ijaraga berishdan tushgan mablag‘ (100%)": "Jami tushum",
                "O‘rmon xo‘jaligida yog‘och kesishdan tushgan mablag‘ (50%)": "Jami tushum",
                "Boshqa daromadlar (10%)": "Jami tushum",
            },
            "ru": {
                "Поступления за рассмотрение заявок и выдачу разрешений (1001)": "Общий доход",
                "Взысканные средства за ущерб животному и растительному миру (1007)": "Общий доход",
                "Поступления за охоту в разрешённых зонах (50%)": "Общий доход",
                "Поступления от использования богатств и культурного наследия земель лесного фонда (100%)": "Общий доход",
                "Поступления от лесного хозяйства за вырубку древесины (50%)": "Общий доход",
                "Прочие доходы (101)": "Общий доход",
            },
        }

        # Filter qilish uchun faqat UZdagi `parent__title` lar olinadi
        all_titles_labels = list(titles_map["uz"].keys())
        all_titles = list(set(titles_map["uz"].values()))

        items = (
            ReportItem.objects.filter(
                statement_column__parent__title__in=all_titles_labels,
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .annotate(value_as_int=Cast("inners__value", IntegerField()))
            .values("statement_column__title")
            .annotate(total=Sum("value_as_int"))
        )

        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Tanlangan til bo‘yicha chiqish
        ilova = {label: result_map.get(title, 0) for label, title in titles_map[lang].items()}

        data = {
            "Jamg'arma" if lang == "uz" else "Фонд": ilova
        }

        return Response(data, status=status.HTTP_200_OK)
