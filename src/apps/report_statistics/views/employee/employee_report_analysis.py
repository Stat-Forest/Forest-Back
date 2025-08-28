from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem
from apps.reports.models import Report

FIELD_NAMES = {
    "uz": {
        "region": "Hudud",
        "ilova4": "4-ilova",
        "ilova5": "5-ilova",
        "ilova6": "6-ilova",
    },
    "ru": {
        "region": "Регион",
        "ilova4": "4-ilova",
        "ilova5": "5-ilova",
        "ilova6": "6-ilova",
    },
}

# Region labels to match RegionChoices.value
REGION_LABELS = {
    "tashkent": {"uz": "Toshkent", "ru": "Ташкент"},
    "namangan": {"uz": "Namangan", "ru": "Наманган"},
    "andijon": {"uz": "Andijon", "ru": "Андижан"},
    "fargona": {"uz": "Farg‘ona", "ru": "Фергана"},
    "buxoro": {"uz": "Buxoro", "ru": "Бухара"},
    "samarqand": {"uz": "Samarqand", "ru": "Самарканд"},
    "navoiy": {"uz": "Navoiy", "ru": "Навои"},
    "qashqadaryo": {"uz": "Qashqadaryo", "ru": "Кашкадарья"},
    "surxondaryo": {"uz": "Surxondaryo", "ru": "Сурхандарья"},
    "xorazm": {"uz": "Xorazm", "ru": "Хорезм"},
    "sirdaryo": {"uz": "Sirdaryo", "ru": "Сырдарья"},
    "jizzax": {"uz": "Jizzax", "ru": "Джизак"},
    "qoraqalpogiston": {"uz": "Qoraqalpog‘iston", "ru": "Каракалпакстан"},
    "republic": {"uz": "Respublika tashkilotlari", "ru": "Республиканские организации"},
}


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
        field_names = FIELD_NAMES[lang]

        # all titles for query
        all_titles = []
        for section_titles in translated.values():
            all_titles.extend([uz if lang == 'uz' else ru for uz, ru in section_titles])

        title_key = 'statement_column__title' if lang == 'uz' else 'statement_column__title_ru'

        # 🔑 Faqat accepted statusdagi hisobotlarni olish
        qs = (
            ReportItem.objects.filter(
                **{f'{title_key}__in': all_titles},
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
            )
            .values('report__organization__region', title_key)
            .annotate(total=Sum(Cast('inners__value', FloatField())))
        )

        grouped_data = defaultdict(lambda: defaultdict(float))
        for item in qs:
            region = item['report__organization__region']
            title = item[title_key]
            total = item['total'] or 0
            grouped_data[region][title] = total

        data = [{field_names["ilova4"]: [], field_names["ilova5"]: [], field_names["ilova6"]: []}]

        for region_key, _ in RegionChoices.choices:
            region_name = REGION_LABELS.get(region_key, {}).get(lang, region_key)

            for key, label in [('4', field_names["ilova4"]),
                               ('5', field_names["ilova5"]),
                               ('6', field_names["ilova6"])]:
                titles = translated[key]
                data[0][label].append({
                    field_names["region"]: region_name,
                    **{
                        (ru if lang == 'ru' else uz): grouped_data[region_key].get(
                            (ru if lang == 'ru' else uz), 0
                        ) for uz, ru in titles
                    }
                })

        return Response(data, status=HTTP_200_OK)
