from collections import defaultdict

from django.utils import translation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

COLUMN_NAMES = [
    "Ruxsatnoma olish uchun arizalarni ko‘rib chiqqanlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (100%)",
    "Hayvonot va o‘simlik dunyosiga yetkazilgan zararni qoplash bo‘yicha undirilgan mablag‘ (100%)",
    "Ruxsat etilgan hududlarda chorva boqish, pichan o‘rish, asalarilar uyasi va qutilarini joylashtirish, daraxt kesmagan holda o‘tin yig‘ish va boshqa maqsadlardan tushgan mablag‘ (50%)",
    "O‘rmon fondi yerlaridagi bog‘lar va madaniy o‘rmonzorlani fuqarolarga ijaraga berishdan tushgan mablag‘ (100%)",
    "O‘rmon xo‘jaligida yog‘och kesishdan tushgan mablag‘ (50%)",
    "Boshqa daromadlar (10%)"
]

ORDERINGS = [
    "1.1.8.1",
    "1.1.7.1",
    "1.1.6.1",
    "1.1.5.1",
    "1.1.4.1",
    "1.1.3.1",
]

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
    description="Orderings va ORM orqali jami tushumlarni hisoblaydi",
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
            description="Deadline UUID bo‘yicha filter",
            required=False,
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatisticsFinanceFundAPIView(APIView):

    def aggregate_by_ordering(self, orderings, deadline_id=None):
        filters = {
            "statement_column__ordering__in": orderings,
            "report__is_report": True,
            # "report__status": Report.StatusChoices.ACCEPTED,
            "statement_column__statement__name": "Jamg'arma",
        }
        if deadline_id:
            filters["report__deadline_id"] = deadline_id

        # ORM bilan filterlangan itemlarni oling
        qs = ReportItem.objects.filter(**filters).prefetch_related("inners", "report__organization")

        # Region va column bo‘yicha summalash
        grouped = defaultdict(float)
        for item in qs:
            region = item.report.organization.region
            ordering = item.statement_column.ordering
            # Column nomini olish
            try:
                idx = ORDERINGS.index(ordering)
                column_name = COLUMN_NAMES[idx]
            except ValueError:
                continue

            # item.inners ichidagi barcha value larni yig‘ish
            total = sum(float(inner.value) for inner in item.inners.all())
            grouped[(region, column_name)] += total

        return grouped

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        grouped = self.aggregate_by_ordering(ORDERINGS, deadline_id)

        # Natijani region bo‘yicha to‘g‘ri tuzish
        data = []
        for region_key, region_label in RegionChoices.choices:
            row = {field_names["region"]: str(region_label)}
            for column_name in COLUMN_NAMES:
                row[column_name] = grouped.get((region_key, column_name), 0)
            data.append(row)

        return Response({field_names["jamgarma"]: data}, status=HTTP_200_OK)
