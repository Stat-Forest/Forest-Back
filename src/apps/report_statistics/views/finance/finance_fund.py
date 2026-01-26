from collections import defaultdict

from django.utils import translation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# "Jami tushum" childlarining ordering'lari
ORDERINGS = [
    "1.1.3.1",  # Ruxsatnoma olish uchun arizalarni... - Jami tushum
    "1.1.4.1",  # Hayvonot va o'simlik dunyosiga... - Jami tushum
    "1.1.5.1",  # Ruxsat etilgan hududlarda chorva boqish... - Jami tushum
    "1.1.6.1",  # O'rmon fondi yerlaridagi bog'lar... - Jami tushum
    "1.1.7.1",  # O'rmon xo'jaligida yog'och kesishdan... - Jami tushum
    "1.1.8.1",  # Boshqa daromadlar - Jami tushum
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
            description="Deadline UUID bo'yicha filter",
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
        qs = ReportItem.objects.filter(**filters).prefetch_related(
            "inners",
            "report__organization",
            "statement_column__parent"  # Parent ma'lumotlarini ham olamiz
        )

        # Region va column bo'yicha summalash
        grouped = defaultdict(float)
        for item in qs:
            region = item.report.organization.region

            # Parent title + "Jami tushum" ni column nomi sifatida ishlatish
            parent_title = item.statement_column.parent.title if item.statement_column.parent else ""
            column_name = f"{parent_title} - Jami tushum"

            # item.inners ichidagi barcha value larni yig'ish
            total = sum(float(inner.value or 0) for inner in item.inners.all())
            grouped[(region, column_name)] += total

        return grouped

    def get_column_names_from_db(self, orderings):
        """Database'dan parent title'larni olish"""
        from apps.reports.models import StatementColumn

        columns = StatementColumn.objects.filter(
            ordering__in=orderings
        ).select_related('parent')

        column_names = {}
        for column in columns:
            parent_title = column.parent.title if column.parent else ""
            column_name = f"{parent_title} - Jami tushum"
            column_names[column.ordering] = column_name

        return column_names

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        grouped = self.aggregate_by_ordering(ORDERINGS, deadline_id)

        # Database'dan column nomlarini olish
        column_names_map = self.get_column_names_from_db(ORDERINGS)

        # Natijani region bo'yicha to'g'ri tuzish
        data = []
        for region_key, region_label in RegionChoices.choices:
            row = {field_names["region"]: str(region_label)}

            # Har bir ordering uchun column nomini database'dan olamiz
            for ordering in ORDERINGS:
                column_name = column_names_map.get(ordering, f"Unknown - Jami tushum")
                row[column_name] = grouped.get((region_key, column_name), 0)

            data.append(row)

        return Response({field_names["jamgarma"]: data}, status=HTTP_200_OK)