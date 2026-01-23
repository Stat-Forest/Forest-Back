from collections import defaultdict

from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from django.utils import translation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

FIELD_NAMES = {
    "uz": {
        "region": "hudud",
        "ilova1": "1-ilova",
        "ilova2": "2-ilova",
        "ilova3": "3-ilova",
    },
    "ru": {
        "region": "регион",
        "ilova1": "1-ilova",
        "ilova2": "2-ilova",
        "ilova3": "3-ilova",
    },
}


@extend_schema(
    summary="Xodim hisobi",
    description="Xodim hisobi (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
            description="Deadline ID bo‘yicha filter",
            required=False,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class StatisticsEmployeeReportAPIView(APIView):
    # 🔹 ordering → label mapping
    ORDERING_MAP = {
        "1": {
            "1.1.1.3.1": "Boshqaruv xodimlari",
            "1.1.1.3.2": "Mutaxassislar",
            "1.1.1.3.3": "Ishlab chiqarish xodimlari",
            "1.1.1.3.4": "Texnik hodim",
            "1.1.1.3.5": "Xizmat korsatuvchi xodimlar",
            "1.1.1.3.6": "ishchilar",
        },
        "2": {
            "2.1.4.1": "Oliy",
            "2.1.4.2": "O`rta-mahsus",
            "2.1.4.3": "O'rta-maxsus",
        },
        "3": {
            "3.1.3.1": "Doimiy",
            "3.1.3.2": "Mavsumiy",
        },
    }

    def aggregate_by_ordering(self, orderings, deadline_id=None):
        filters = {
            "statement_column__ordering__in": orderings,
            "report__is_report": True,
            "report__status": Report.StatusChoices.ACCEPTED,
        }

        if deadline_id:
            filters["report__deadline_id"] = deadline_id

        return (
            ReportItem.objects
            .filter(**filters)
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

        grouped = defaultdict(lambda: defaultdict(float))

        for block, mapping in self.ORDERING_MAP.items():
            qs = self.aggregate_by_ordering(mapping.keys(), deadline_id)

            for item in qs:
                region = item["report__organization__region"]
                ordering = item["statement_column__ordering"]
                title = mapping[ordering]

                grouped[(block, region)][title] += item["total"] or 0

        data = [{
            field_names["ilova1"]: [],
            field_names["ilova2"]: [],
            field_names["ilova3"]: [],
        }]

        for region_key, region_label in RegionChoices.choices:
            region_name = str(region_label)

            for block, ilova_key in [
                ("1", "ilova1"),
                ("2", "ilova2"),
                ("3", "ilova3"),
            ]:
                row = {field_names["region"]: region_name}

                for title in self.ORDERING_MAP[block].values():
                    row[title] = grouped[(block, region_key)].get(title, 0)

                data[0][field_names[ilova_key]].append(row)

        return Response(data, status=HTTP_200_OK)
