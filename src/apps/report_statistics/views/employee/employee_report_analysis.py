from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem


@extend_schema(
    summary="Xodim hisobi tahlili",
    description="Xodim hisobi tahlili (UZ va RU tillarini qo‘llab-quvvatlaydi)",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name='lang',
            description='Til parametri: uz (default) yoki ru',
            required=False,
            type=OpenApiTypes.STR,
            enum=['uz', 'ru'],
            location=OpenApiParameter.QUERY
        )
    ]
)
class StatisticsEmployeeReportAnalysisAPIView(APIView):

    def get_translated_titles(self, lang):
        return {
            '4': [
                ("Tasdiqlangan shtat birligi bo‘yicha xodimlar soni (faqat boshqaruv xodimlari)",
                 "Количество сотрудников по утвержденной штатной единице (только управленческий состав)"),
                ("Amaldagi xodimlar soni (faqat boshqaruv xodimlari)",
                 "Фактическое количество сотрудников (только управленческий состав)"),
                ("2 yilgacha", "До 2 лет"),
                ("2 yildan ortiq", "Свыше 2 лет"),
                ("PHD, fan nomzodi ilmiy darajasiga ega xodimlar soni",
                 "Количество сотрудников с ученой степенью PhD, кандидата наук"),
                ("Xalqaro sertifikatga ega xodimlar soni",
                 "Количество сотрудников с международным сертификатом"),
            ],
            '5': [
                ("30 yoshdan 50 yoshgacha bo‘lgan xodimlar soni",
                 "Количество сотрудников от 30 до 50 лет"),
                ("50 yoshdan yuqori bo‘lgan xodimlar soni",
                 "Количество сотрудников старше 50 лет"),
                ("Mablag‘ sarfi, mln. so‘mda",
                 "Расход средств, в млн. сумов"),
                ("Yuqori lavozimlar", "Высшие должности"),
                ("Quyi lavozimlar", "Низшие должности")
            ],
            '6': [
                ("O'rta malumotli", "Со средним образованием")
            ]
        }

    def get(self, request):
        lang = request.query_params.get('lang', 'uz')
        if lang not in ['uz', 'ru']:
            lang = 'uz'

        translated = self.get_translated_titles(lang)

        # all titles for query
        all_titles = []
        for section_titles in translated.values():
            all_titles.extend([uz if lang == 'uz' else ru for uz, ru in section_titles])

        title_key = 'statement_column__title' if lang == 'uz' else 'statement_column__title_ru'

        qs = (
            ReportItem.objects.filter(**{f'{title_key}__in': all_titles})
            .values('report__organization__region', title_key)
            .annotate(total=Sum(Cast('inners__value', FloatField())))
        )

        grouped_data = defaultdict(lambda: defaultdict(float))
        for item in qs:
            region = item['report__organization__region']
            title = item[title_key]
            total = item['total'] or 0
            grouped_data[region][title] = total

        data = [{
            '4-ilova': [],
            '5-ilova': [],
            '6-ilova': []
        }]

        for region in RegionChoices.values:
            for key, label in [('4', '4-ilova'), ('5', '5-ilova'), ('6', '6-ilova')]:
                titles = translated[key]
                data[0][label].append({
                    'name': region,
                    **{
                        (ru if lang == 'ru' else uz): grouped_data[region].get(
                            (ru if lang == 'ru' else uz), 0
                        )
                        for uz, ru in titles
                    }
                })

        return Response(data, status=HTTP_200_OK)
