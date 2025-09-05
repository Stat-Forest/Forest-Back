from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from collections import defaultdict

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report


FIELD_NAMES = {
    "uz": {
        "region": "Hudud",
        "by_income_types": "1-ilova",
    },
    "ru": {
        "region": "Регион",
        "by_income_types": "1-ilova",
    },
}

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

# Tarjima qilinadigan subcolumns
SUB_TITLES = {
    "uz": ["Reja", "Amalda"],
    "ru": ["План", "Факт"],
}

rows = [
    ("Yirik hajmli yopiq ildizli ko'chatlar yetishtirish miqdori",
     "Количество выращивания крупногабаритных саженцев с закрытым корнем", False, "YILLIK_TOTAL"),
    ("Tyanshan qoraqarag'ay", "Тяньшанский черный карагач", True, "YILLIK"),
    ("Tyanshan qarag'ayi", "Тяньшанский карагач", True, "YILLIK"),
    ("Virdjiniya archa", "Верджинская арча", True, "YILLIK"),
    ("Sharq tuya", "Восточная туя", True, "YILLIK"),
    ("Eldor qarag'ay", "Елдорский карагач", True, "YILLIK"),
    ("Qrim qarag'ayi", "Крымский карагач", True, "YILLIK"),
    ("Tuya sharq", "Туя восточная", True, "YILLIK"),
    ("Kiparis", "Кипарис", True, "YILLIK"),
    ("Qayrag'och", "Кайрагач", True, "YILLIK"),
    ("Shumtol", "Шумтол", True, "YILLIK"),
    ("Zarang", "Заранг", True, "YILLIK"),
    ("Sadaqayrag'och", "Садакайраггач", True, "YILLIK"),
    ("Yapon saforasi", "Японский кипарис", True, "YILLIK"),
    ("Akatsiya", "Акация", True, "YILLIK"),
    ("Ipak akatsiya", "Шелковая акация", True, "YILLIK"),
    ("Aylant", "Айлант", True, "YILLIK"),
    ("Katalpa", "Катальпа", True, "YILLIK"),
    ("Pavloniya", "Павлония", True, "YILLIK"),
    ("Chinar", "Тополь", True, "YILLIK"),
    ("Kashtan", "Каштан", True, "YILLIK"),
    ("Pisardi", "Писарди", True, "YILLIK"),
    ("Bag'rik", "Багрянник", True, "YILLIK"),
    ("Qora tut", "Шелковица черная", True, "YILLIK"),
    ("Yapon tut", "Японская шелковица", True, "YILLIK"),
    ("Eman", "Еман", True, "YILLIK"),
    ("Oqqayin", "Белая акация", True, "YILLIK"),
    ("Boshqa turlar", "Другие виды", True, "YILLIK"),
    ("Atirgul", "Роза", True, "YILLIK"),
]


@extend_schema(
    summary="Yopiq ildiz yirik hajmli",
    description="Yopiq ildiz yirik hajmli (UZ va RU tillarini qo‘llab-quvvatlaydi)",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatisticsClosedRootAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        field_names = FIELD_NAMES[lang]
        sub_titles = SUB_TITLES[lang]

        # === titles dynamic from rows ===
        all_titles = []
        title_map = {}  # parent -> [subtitles]
        for title_uz, title_ru, has_children, plan_status in rows:
            parent_title = title_uz if lang == "uz" else title_ru
            title_map[parent_title] = sub_titles
            all_titles.extend(sub_titles)

        title_key_parent = (
            "statement_column__parent__title_uz"
            if lang == "uz"
            else "statement_column__parent__title_ru"
        )
        title_key = (
            "statement_column__title_uz"
            if lang == "uz"
            else "statement_column__title_ru"
        )

        qs = (
            ReportItem.objects.filter(
                report__is_report=True,
                report__status=Report.StatusChoices.ACCEPTED,
                report__statement__name='O‘rmon bilan qoplangan yerlar',
                **{f"{title_key}__in": all_titles}
            )
            .values("report__organization__region", title_key_parent, title_key)
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        # Group: region -> {parent -> {sub -> value}}
        grouped_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for item in qs:
            region = item["report__organization__region"]
            parent = item[title_key_parent]
            sub = item[title_key]
            grouped_data[region][parent][sub] = item["total"] or 0

        # Build response
        data = [{field_names["by_income_types"]: []}]
        for region_key, _ in RegionChoices.choices:
            region_name = REGION_LABELS.get(region_key, {}).get(lang, region_key)

            region_entry = {field_names["region"]: region_name}

            for parent_title, subtitles in title_map.items():
                for sub in subtitles:
                    combined_title = f"{parent_title} - {sub}"
                    region_entry[combined_title] = grouped_data[region_key][parent_title].get(sub, 0)

            data[0][field_names["by_income_types"]].append(region_entry)

        return Response(data, status=HTTP_200_OK)
