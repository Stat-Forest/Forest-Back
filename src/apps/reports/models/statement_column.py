from collections import defaultdict

from django.db.models import Sum, FloatField, Q
from django.db.models.functions import Cast

from django.utils import translation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import Report, StatementColumn
from apps.reports.models.report_item import ReportItem

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# Children ordering'lar va ularning nomlari
CHILDREN_ORDERINGS = {
    "1.1.3.1": "Ruxsatnoma olish uchun arizalarni ko'rib chiqqanlik va ruxsatnomalar berganlik uchun tushgan mablag' (100%) - Jami tushum",
    "1.1.4.1": "Hayvonot va o'simlik dunyosiga yetkazilgan zararni qoplash bo'yicha undirilgan mablag' (100%) - Jami tushum",
    "1.1.5.1": "Ruxsat etilgan hududlarda chorva boqish, pichan o'rish, asalarilar uyasi va qutilarini joylashtirish, daraxt kesmagan holda o'tin yig'ish va boshqa maqsadlardan tushgan mablag' (50%) - Jami tushum",
    "1.1.6.1": "O'rmon fondi yerlaridagi bog'lar va madaniy o'rmonzorlani fuqarolarga ijaraga berishdan tushgan mablag' (100%) - Jami tushum",
    "1.1.7.1": "O'rmon xo'jaligida yog'och kesishdan tushgan mablag' (50%) - Jami tushum",
    "1.1.8.1": "Boshqa daromadlar (10%) - Jami tushum",
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
    description="Jami tushumlarni hudud bo'yicha hisoblaydi",
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
        ordering_filter = Q(statement_column__ordering__in=CHILDREN_ORDERINGS.keys())

        # Statement nomi bo'yicha filter qo'shamiz
        # StatementColumn -> Statement munosabatidan foydalanamiz
        from apps.reports.models import Statement
        jamgarma_statements = Statement.objects.filter(name="Jamg'arma")
        statement_ids = list(jamgarma_statements.values_list('id', flat=True))

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

            # Faqat bizning CHILDREN_ORDERINGS ichida bo'lgan ordering'larni qo'shamiz
            if ordering in CHILDREN_ORDERINGS:
                title = CHILDREN_ORDERINGS[ordering]
                grouped[region][title] += item["total"] or 0

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