from collections import defaultdict
from uuid import UUID

from django.db.models import Sum, FloatField
from django.utils import translation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import ReportItem, Report
from apps.utils.services import RegionChoices

JAMI_TUSHUM_ORDERINGS = [
    "1.1.3.1", "1.1.4.1", "1.1.5.1",
    "1.1.6.1", "1.1.7.1", "1.1.8.1"
]

COLUMN_NAMES = [
    "Ruxsatnoma olish uchun arizalarni ko‘rib chiqqanlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (100%)",
    "Hayvonot va o‘simlik dunyosiga yetkazilgan zararni qoplash bo‘yicha undirilgan mablag‘ (100%)",
    "Ruxsat etilgan hududlarda chorva boqish, pichan o‘rish, asalarilar uyasi va qutilarini joylashtirish, daraxt kesmagan holda o‘tin yig‘ish va boshqa maqsadlardan tushgan mablag‘ (50%)",
    "O‘rmon fondi yerlaridagi bog‘lar va madaniy o‘rmonzorlani fuqarolarga ijaraga berishdan tushgan mablag‘ (100%)",
    "O‘rmon xo‘jaligida yog‘och kesishdan tushgan mablag‘ (50%)",
    "Boshqa daromadlar (10%)"
]

REGION_MAP_OVERRIDE = {
    "Respublika": "Respublika tashkilotlari"  # bazadagi region nomini frontend labelga moslashtiramiz
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
    def get_aggregated_data(self, orderings, deadline_id=None):
        filters = {
            "statement_column__ordering__in": orderings,
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
        }

        if deadline_id:
            filters["report__deadline_id"] = deadline_id

        queryset = (
            ReportItem.objects
            .filter(**filters)
            .values(
                "report__organization__region",
                "statement_column__ordering",
                "value"
            )
        )
        return queryset

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        translation.activate(lang)

        deadline_id = request.query_params.get("deadline")
        if deadline_id:
            try:
                UUID(deadline_id)
            except ValueError:
                return Response({"detail": "Invalid deadline UUID"}, status=HTTP_400_BAD_REQUEST)

        # Regionlar bazasi
        data = []
        for _, region_label in RegionChoices.choices:
            region_dict = {"region": str(region_label)}
            for col in COLUMN_NAMES:
                region_dict[col] = 0
            region_dict["Jami tushum"] = 0
            data.append(region_dict)

        region_map = {r["region"]: r for r in data}

        ordering_to_column = {
            "1.1.3.1": COLUMN_NAMES[0],
            "1.1.4.1": COLUMN_NAMES[1],
            "1.1.5.1": COLUMN_NAMES[2],
            "1.1.6.1": COLUMN_NAMES[3],
            "1.1.7.1": COLUMN_NAMES[4],
            "1.1.8.1": COLUMN_NAMES[5],
        }

        queryset = self.get_aggregated_data(JAMI_TUSHUM_ORDERINGS, deadline_id)

        for item in queryset:
            region_key = item["report__organization__region"]
            region_key = REGION_MAP_OVERRIDE.get(region_key, region_key)  # agar respub. bo‘lsa o‘zgartiramiz
            ordering = item["statement_column__ordering"]
            raw_value = item["value"] or 0

            if isinstance(raw_value, str):
                raw_value = float(raw_value.replace(",", "."))

            if region_key not in region_map:
                continue

            region_data = region_map[region_key]
            col_name = ordering_to_column.get(ordering)
            if col_name:
                region_data[col_name] += raw_value
                region_data["Jami tushum"] += raw_value

        return Response(data, status=HTTP_200_OK)
