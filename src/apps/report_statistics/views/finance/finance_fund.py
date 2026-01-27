from collections import defaultdict

from django.db.models import Sum, FloatField, Q
from django.db.models.functions import Cast
from decimal import Decimal, InvalidOperation

from django.utils import translation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report, ReportItemInner, StatementColumn
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# Parent ordering'lar
PARENT_ORDERINGS = [
    "1.1.3",
    "1.1.4",
    "1.1.5",
    "1.1.6",
    "1.1.7",
    "1.1.8",
]

# Children ordering'lar va ularning nomlari
CHILDREN_ORDERINGS = {
    "1.1.3.1": "Ruxsatnoma olish uchun arizalarni... - Jami tushum",
    "1.1.4.1": "Hayvonot va o'simlik dunyosiga... - Jami tushum",
    "1.1.5.1": "Ruxsat etilgan hududlarda chorva boqish... - Jami tushum",
    "1.1.6.1": "O'rmon fondi yerlaridagi bog'lar... - Jami tushum",
    "1.1.7.1": "O'rmon xo'jaligida yog'och kesishdan... - Jami tushum",
    "1.1.8.1": "Boshqa daromadlar - Jami tushum",
}

FIELD_NAMES = {
    "uz": {
        "region": "hudud",
        "jamgarma": "Jamg'arma",
    },
    "ru": {
        "region": "регион",
        "jamgarma": "Фонд",
    },
}


@extend_schema(
    summary="Jamg'arma",
    description="Parent va children orderings bo'yicha jami tushumlarni hisoblaydi",
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
class StatisticsFinanceFundAPIView(APIView):

    def aggregate_by_ordering(self, parent_orderings, children_orderings, deadline_id=None):
        """
        Parent va children ordering'lar bo'yicha ma'lumotlarni agregatsiya qiladi.
        Parent yoki children ordering'ga mos keladigan barcha yozuvlarni oladi.
        """
        filters = Q(statement_column__ordering__in=children_orderings)

        # Parent ordering'lar uchun ham filter qo'shamiz
        for parent in parent_orderings:
            filters |= Q(statement_column__ordering__startswith=f"{parent}.")

        base_filters = {
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
            "statement_column__statement__name": "Jamg'arma",
        }

        if deadline_id:
            base_filters["report__deadline_id"] = deadline_id

        return (
            ReportItem.objects
            .filter(filters, **base_filters)
            .values(
                "report__organization__region",
                "statement_column__ordering",
            )
            .annotate(total=Sum(Cast("inners__value", FloatField())))
        )

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        # Ma'lumotlarni agregatsiya qilish (parent va children ordering'lar bo'yicha)
        qs = self.aggregate_by_ordering(
            PARENT_ORDERINGS,
            list(CHILDREN_ORDERINGS.keys()),
            deadline_id
        )

        # Har bir hudud va ordering uchun ma'lumotlarni guruhlash
        grouped = defaultdict(lambda: defaultdict(float))

        for item in qs:
            region = item["report__organization__region"]
            ordering = item["statement_column__ordering"]

            # Ordering'ni children ordering'larga moslashtirish
            # Agar to'g'ridan-to'g'ri children ordering bo'lsa
            if ordering in CHILDREN_ORDERINGS:
                title = CHILDREN_ORDERINGS[ordering]
                grouped[region][title] += item["total"] or 0
            else:
                # Agar parent ordering ostidagi boshqa children bo'lsa,
                # tegishli parent children'ga qo'shamiz
                for child_ordering, title in CHILDREN_ORDERINGS.items():
                    parent = ".".join(child_ordering.split(".")[:-1])
                    if ordering.startswith(f"{parent}."):
                        grouped[region][title] += item["total"] or 0
                        break

        # Javob formatini yaratish
        data = []

        for region_key, region_label in RegionChoices.choices:
            region_name = str(region_label)

            row = {field_names["region"]: region_name}

            # Har bir "Jami tushum" uchun qiymat qo'shish
            for ordering, title in CHILDREN_ORDERINGS.items():
                row[title] = grouped[region_key].get(title, 0)

            data.append(row)

        return Response(data, status=HTTP_200_OK)