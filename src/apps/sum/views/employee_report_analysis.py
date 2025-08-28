from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.reports.models import ReportItem, Report


@extend_schema(
    summary="Xodim hisobi tahlili",
    description="Xodimlar haqidagi ma’lumotlarni 4-ilova va 5-ilova kesimida yig‘ib beradi",
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
class SumEmployeeReportAnalysisListAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        # 4-ilova (yosh, tajriba, sertifikatlar)
        titles_1_map = {
            "uz": {
                "30 yoshgacha bo‘lgan boshqaruv xodimlari": "30 yoshgacha bo‘lgan  boshqaruv xodimlari soni",
                "40–50 yosh oralig‘idagi boshqaruv xodimlari": "40 yoshdan 50 yoshgacha bo‘lgan  boshqaruv xodimlari soni",
                "60 yoshdan yuqori boshqaruv xodimlari": "60 yoshdan yuqori bo‘lgan boshqaruv xodimlari soni",
                "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari": "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari soni",
                "Tajriba – 2 yilgacha": "2 yilgacha",
                "Tajriba – 2 yildan ortiq": "2 yildan ortiq",
                "Xalqaro sertifikatli xodimlar": "Xalqaro sertifikatga ega xodimlar soni",
                "Milliy sertifikatli xodimlar": "Milliy sertifikatga ega xodimlar soni",
            },
            "ru": {
                "Руководители до 30 лет": "30 yoshgacha bo‘lgan  boshqaruv xodimlari soni",
                "Руководители 40–50 лет": "40 yoshdan 50 yoshgacha bo‘lgan  boshqaruv xodimlari soni",
                "Руководители старше 60 лет": "60 yoshdan yuqori bo‘lgan boshqaruv xodimlari soni",
                "Руководители, достигающие пенсионного возраста в 2025 году": "2025 yilda pensiya yoshiga yetadigan boshqaruv xodimlari soni",
                "Опыт – до 2 лет": "2 yilgacha",
                "Опыт – более 2 лет": "2 yildan ortiq",
                "С международным сертификатом": "Xalqaro sertifikatga ega xodimlar soni",
                "С национальным сертификатом": "Milliy sertifikatga ega xodimlar soni",
            }
        }

        # 5-ilova (lavozim va mablag‘)
        titles_4_map = {
            "uz": {
                "Tasdiqlangan shtat birligi bo‘yicha xodimlar": "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
                "Shundan xotin-qizlar": "Shundan xotin-qizlar soni",
                "Mablag‘ sarfi (mln. so‘mda)": "Mablag‘ sarfi, mln. so‘mda",
                "Dam olish/bayramda ishlaganlar": "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
                "Yuqori lavozimdagilar": "Yuqori lavozimlar",
                "Teng lavozimdagilar": "Teng lavozimlar",
                "Quyi lavozimdagilar": "Quyi lavozimlar",
            },
            "ru": {
                "Сотрудники по утвержденной штатной единице": "Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
                "Из них женщины": "Shundan xotin-qizlar soni",
                "Расход средств (млн. сум)": "Mablag‘ sarfi, mln. so‘mda",
                "Работавшие в праздничные/выходные дни": "Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
                "Высшие должности": "Yuqori lavozimlar",
                "Равные должности": "Teng lavozimlar",
                "Низшие должности": "Quyi lavozimlar",
            }
        }

        # Barcha kerakli sarlavhalarni yig‘ish (UZ dagi qiymatlar bo‘yicha!)
        all_titles = list(set(titles_1_map["uz"].values()) | set(titles_4_map["uz"].values()))

        # Ma’lumotlarni yig‘ish va summalash
        items = (
            ReportItem.objects.filter(
                statement_column__title__in=all_titles,
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .values("statement_column__title")
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        # Natijani dict formatga o‘tkazish
        result_map = {item["statement_column__title"]: item["total"] or 0 for item in items}

        # Har bir ilova bo‘yicha tartiblab qaytarish
        ilova_1 = {label: result_map.get(title, 0) for label, title in titles_1_map[lang].items()}
        ilova_4 = {label: result_map.get(title, 0) for label, title in titles_4_map[lang].items()}

        data = [{
            "4-ilova": ilova_1,
            "5-ilova": ilova_4,
        }]

        return Response(data, status=status.HTTP_200_OK)
