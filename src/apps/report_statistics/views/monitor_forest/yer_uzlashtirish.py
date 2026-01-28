from collections import defaultdict

from django.db.models import Sum, FloatField, Q
from django.db.models.functions import Cast
from django.utils import translation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import ReportItem, Report, Statement
from apps.utils.services import RegionChoices


# Yer o‘zlashtirish → Amalda column
AMALDA_ORDERINGS = {
    "1.1.3": "Foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot - amalda",
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
    summary="Yer o‘zlashtirish - Amalda",
    description="Yer o‘zlashtirish statementi uchun 'Amalda' ko‘rsatkichlarini hududlar kesimida hisoblaydi",
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
        ),
    ],
)
class StatisticsYerOzlashtirishAmaldaAPIView(APIView):

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        base_filters = {
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
        }

        if deadline_id:
            base_filters["report__deadline_id"] = deadline_id

        # Statement filter
        statement_ids = Statement.objects.filter(
            name="Yer o‘zlashtirish"
        ).values_list("id", flat=True)

        ordering_filter = Q(
            statement_column__ordering__in=AMALDA_ORDERINGS.keys(),
            statement_column__statement_id__in=statement_ids,
        )

        queryset = (
            ReportItem.objects
            .filter(ordering_filter, **base_filters)
            .values(
                "report__organization__region",
                "statement_column__ordering",
            )
            .annotate(
                total=Sum(Cast("inners__value", FloatField()))
            )
        )

        grouped = defaultdict(lambda: defaultdict(float))

        for item in queryset:
            region = item["report__organization__region"]
            ordering = item["statement_column__ordering"]
            title = AMALDA_ORDERINGS[ordering]

            grouped[region][title] += item["total"] or 0

        data = []

        for region_key, region_label in RegionChoices.choices:
            row = {
                field_names["region"]: str(region_label),
            }

            for title in AMALDA_ORDERINGS.values():
                row[title] = grouped[region_key].get(title, 0)

            data.append(row)

        return Response(data, status=HTTP_200_OK)
