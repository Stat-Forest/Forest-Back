from uuid import UUID
from collections import defaultdict

from django.db.models import Sum, FloatField
from django.db.models.functions import Cast
from django.utils import translation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from apps.reports.models import ReportItem
from apps.utils.services import RegionChoices


@extend_schema(
    summary="Jamg‘arma",
    description="Jamg‘arma (UZ va RU tillarini qo‘llab-quvvatlaydi)",
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
            type=OpenApiTypes.UUID,   # ✅ UUID qilib qo‘shildi
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class StatisticsFinanceFundAPIView(APIView):

    def get(self, request):
        # -----------------------------
        # Language
        # -----------------------------
        lang = request.query_params.get("lang", "uz")
        translation.activate(lang)

        # -----------------------------
        # Filters
        # -----------------------------
        filters = {}

        region = request.query_params.get("region")
        if region:
            filters["organization__region"] = region

        deadline_id = request.query_params.get("deadline")
        if deadline_id:
            try:
                UUID(deadline_id)  # UUID validatsiya
                filters["report__deadline_id"] = deadline_id
            except ValueError:
                return Response(
                    {"detail": "Invalid deadline UUID"},
                    status=400,
                )

        # -----------------------------
        # Queryset
        # -----------------------------
        queryset = (
            ReportItem.objects
            .filter(**filters)
            .select_related(
                "organization",
                "department_column",
            )
            .annotate(
                value_float=Cast("value", FloatField())
            )
        )

        # -----------------------------
        # Aggregation
        # -----------------------------
        result = defaultdict(float)

        for item in queryset:
            key = (
                item.organization.id,
                item.organization.title,
            )
            result[key] += item.value_float or 0

        # -----------------------------
        # Response format
        # -----------------------------
        data = [
            {
                "organization_id": org_id,
                "organization": org_title,
                "total": total,
            }
            for (org_id, org_title), total in result.items()
        ]

        return Response(data, status=HTTP_200_OK)
