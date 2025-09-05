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
        "by_income_types": "2-ilova",
    },
    "ru": {
        "region": "Регион",
        "by_income_types": "2-ilova",
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
    ("Jami", "Итого", True),
    ("Cho'l", "Пустыня", True),
    ("Jami yong'oq mevalar", "Итого ореховые плоды", True),
    ("Shundan", "Из них", False),
    ("Jami tez o'suvchilar", "Итого быстрорастущие", True),
    ("Shundan", "Из них", False),
    ("Tabiiy tiklanishga ko'maklashish va boshqa daraxt turlaridan ekish",
     "Помощь в естественном восстановлении и посадка других видов деревьев", False)
]

@extend_schema(
    summary="O'rmon barpo qilish bo'limi",
    description="O'rmon barpo qilish bo'limi (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
class StatisticsBuildForestAPIView(APIView):
    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        if lang not in ["uz", "ru"]:
            lang = "uz"

        field_names = FIELD_NAMES[lang]

        # Mapping for subcolumns (uz/ru)
        SUB_MAP = {
            "Reja": {"uz": "Reja", "ru": "План"},
            "Amalda": {"uz": "Amalda", "ru": "Факт"},
            "Foiz": {"uz": "Foiz", "ru": "Процент"},
        }

        title_parent = (
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
                report__statement__name="O‘rmon bilan qoplangan yerlar",
            )
            .values("report__organization__region", title_parent, title_key)
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        # Region → parent → child → value
        grouped = defaultdict(lambda: defaultdict(dict))
        for row in qs:
            region = row["report__organization__region"]
            parent = row[title_parent]
            child = row[title_key]
            grouped[region][parent][child] = row["total"] or 0

        # === Response build ===
        data = [{field_names["by_income_types"]: []}]

        for region_key, _ in RegionChoices.choices:
            region_name = REGION_LABELS.get(region_key, {}).get(lang, region_key)
            entry = {field_names["region"]: region_name}

            for title_uz, title_ru, has_sub in rows:
                parent_title = title_uz if lang == "uz" else title_ru
                children = grouped[region_key].get(parent_title, {})

                if parent_title == ("Shundan" if lang == "uz" else "Из них"):
                    # already real children: e.g. Yong‘oq, Pista …
                    for child_name, value in children.items():
                        entry[child_name] = value

                elif has_sub:
                    # build Reja, Amalda, Foiz
                    reja = children.get(SUB_MAP["Reja"][lang], 0)
                    amalda = children.get(SUB_MAP["Amalda"][lang], 0)
                    foiz = round((amalda / reja * 100), 1) if reja else 0

                    entry[f"{parent_title} - {SUB_MAP['Reja'][lang]}"] = reja
                    entry[f"{parent_title} - {SUB_MAP['Amalda'][lang]}"] = amalda
                    entry[f"{parent_title} - {SUB_MAP['Foiz'][lang]}"] = foiz

                else:
                    # Plain parent (like "Tabiiy tiklanishga ...")
                    value = sum(children.values()) if children else 0
                    entry[parent_title] = value

            data[0][field_names["by_income_types"]].append(entry)

        return Response(data, status=HTTP_200_OK)
