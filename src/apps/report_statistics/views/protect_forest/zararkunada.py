from collections import defaultdict

from django.db.models import Sum, FloatField, Q
from django.db.models.functions import Cast

from django.utils import translation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report, Statement
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# "Amalda" column ordering'lari va ularning nomlari
AMALDA_ORDERINGS = {
    "1.1.2.2": "Zararkunanda va kasalliklarni aniqlash bo'yicha o'rganiladigan maydon (gektar) - amalda",
    "1.1.3.2": "Jami: Aniqlangan zararkunanda va kasallikka qarshi kurashish bo'yicha olib boriladigan tadbir (gektar) - amalda",
    "1.1.4.1.2": "Biologik tadbir (oltinkoʻz, trixogramma, brokon) gektar - amalda",
    "1.1.4.2.1": "Kimyoviy ishlov yordamida (gektar) - amalda",
    "1.1.4.3.1": "Mexanik, agrotexnik (qo'l kuchi yordamida zararlangan shoxlardan tozalash) gektar - amalda",
}

FIELD_NAMES = {
    "uz": {
        "region": "hudud",
    },
    "ru": {
        "region": "регион",
    },
}


@extend_schema(
    summary="Zararkunanda - Amalda",
    description="Zararkunanda va kasalliklarga qarshi kurashish statement uchun 'Amalda' ko'rsatkichlarini hudud bo'yicha hisoblaydi",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="deadline",
            description="Deadline UUID bo'yicha filter",
            required=False,
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatisticsZararkunandaAPIView(APIView):

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        # Base filters
        base_filters = {
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
        }

        if deadline_id:
            base_filters["report__deadline_id"] = deadline_id

        # Filter faqat kerakli ordering'lar bo'yicha
        ordering_filter = Q(statement_column__ordering__in=AMALDA_ORDERINGS.keys())

        # Statement nomi bo'yicha filter qo'shamiz
        zararkunanda_statements = Statement.objects.filter(
            name="Zararkunanda va kasalliklarga qarshi kurashish"
        )
        statement_ids = list(zararkunanda_statements.values_list('id', flat=True))

        if statement_ids:
            ordering_filter &= Q(statement_column__statement_id__in=statement_ids)

        # Ma'lumotlarni olish
        queryset = (
            ReportItem.objects
            .filter(ordering_filter, **base_filters)
            .values(
                "report__organization__region",
                "statement_column__ordering",
            )
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

        # Har bir hudud va ordering uchun ma'lumotlarni guruhlash
        grouped = defaultdict(lambda: defaultdict(float))

        for item in queryset:
            region = item["report__organization__region"]
            ordering = item["statement_column__ordering"]

            # Faqat bizning AMALDA_ORDERINGS ichida bo'lgan ordering'larni qo'shamiz
            if ordering in AMALDA_ORDERINGS:
                title = AMALDA_ORDERINGS[ordering]
                grouped[region][title] += item["total"] or 0

        # Javob formatini yaratish
        data = []

        for region_key, region_label in RegionChoices.choices:
            region_name = str(region_label)

            row = {field_names["region"]: region_name}

            # Har bir "Amalda" uchun qiymat qo'shish
            for ordering, title in AMALDA_ORDERINGS.items():
                row[title] = grouped[region_key].get(title, 0)

            data.append(row)

        return Response(data, status=HTTP_200_OK)