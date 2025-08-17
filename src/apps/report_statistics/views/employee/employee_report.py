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
    summary="Xodim hisobi",
    description="Xodim hisobi (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class StatisticsEmployeeReportAPIView(APIView):

    def get_translated_titles(self, lang):
        titles = {
            'uz': {
                '1': ["Boshqaruv xodimlari", "Mutaxassislar", "Ishlab chiqarish xodimlari",
                      "Texnik hodim", "Xizmat korsatuvchi xodimlar", "ishchilar"],
                '2': ["Oliy", "O`rta maxsus", "O`rta", "Ayol", "Erkak xodimlar", "Yoshlar Jami"],
                '3': ["Doimiy", "Mavsumiy", "Temir daftar va ayollar daftariga kiritilgan",
                      "Kambag’al axolidan olingan", "Kasanachilik asosida"]
            },
            'ru': {
                '1': ["Руководящие работники", "Специалисты", "Производственные работники",
                      "Технический персонал", "Обслуживающий персонал", "Рабочие"],
                '2': ["Высшее", "Среднее специальное", "Среднее", "Женщины", "Мужчины", "Всего молодёжи"],
                '3': ["Постоянные", "Сезонные", "Включённые в железную и женскую книги",
                      "Из числа малообеспеченных", "На основе надомного труда"]
            }
        }
        return titles[lang]

    def get_aggregated_data_by_titles(self, titles, lang, parent_title=None):
        filter_key = 'statement_column__title' if lang == 'uz' else 'statement_column__title_ru'
        parent_key = 'statement_column__parent__title' if lang == 'uz' else 'statement_column__parent__title_ru'

        filters = {f'{filter_key}__in': titles}
        if parent_title:
            filters[parent_key] = parent_title

        # endi ReportItemInner.value ishlatiladi
        return (
            ReportItem.objects.filter(**filters)
            .values('report__organization__region', filter_key)
            .annotate(
                total=Sum(Cast('inners__value', FloatField()))
            )
        )

    def get(self, request):
        lang = request.query_params.get('lang', 'uz')  # default is 'uz'
        if lang not in ['uz', 'ru']:
            lang = 'uz'

        translated_titles = self.get_translated_titles(lang)

        # Translate parent title if needed
        parent_title_ilova_1 = "Shundan-1" if lang == 'uz' else "Из них-1"

        qs1 = self.get_aggregated_data_by_titles(translated_titles['1'], lang, parent_title=parent_title_ilova_1)
        qs2 = self.get_aggregated_data_by_titles(translated_titles['2'], lang)
        qs3 = self.get_aggregated_data_by_titles(translated_titles['3'], lang)

        title_key = 'statement_column__title' if lang == 'uz' else 'statement_column__title_ru'

        grouped_data = defaultdict(lambda: defaultdict(float))

        for qs in (qs1, qs2, qs3):
            for item in qs:
                region = item['report__organization__region']
                title = item[title_key]
                total = item['total'] or 0
                grouped_data[region][title] += total

        data = [{
            '1-ilova': [],
            '2-ilova': [],
            '3-ilova': []
        }]

        for region in RegionChoices.values:
            data[0]['1-ilova'].append({
                'name': region,
                **{title: grouped_data[region].get(title, 0) for title in translated_titles['1']}
            })
            data[0]['2-ilova'].append({
                'name': region,
                **{title: grouped_data[region].get(title, 0) for title in translated_titles['2']}
            })
            data[0]['3-ilova'].append({
                'name': region,
                **{title: grouped_data[region].get(title, 0) for title in translated_titles['3']}
            })

        return Response(data, status=HTTP_200_OK)
