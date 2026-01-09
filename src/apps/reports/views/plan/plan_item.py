from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import (
    Plan,
    PlanItem,
    PlantPlanItem,
    StatementColumn,
)
from apps.reports.serializers.plan import (
    ColumnPlanItemSerializer,
    PlantPlanGroupSerializer,
)


@extend_schema(
    tags=["PlanItem"],
    parameters=[
        OpenApiParameter("organization", OpenApiTypes.UUID, required=True),
        OpenApiParameter("statement", OpenApiTypes.UUID, required=True),
        OpenApiParameter("year", OpenApiTypes.INT, required=True),
        OpenApiParameter("season", OpenApiTypes.STR, required=False),
        OpenApiParameter("lang", OpenApiTypes.STR, required=False),
    ]
)
class PlanItemDetailAPIView(APIView):

    def get(self, request, *args, **kwargs):
        lang = request.query_params.get("lang", "uz")

        plan_filters = {
            "organization": request.query_params.get("organization"),
            "statement": request.query_params.get("statement"),
            "year": request.query_params.get("year"),
        }

        season = request.query_params.get("season")
        if season:
            plan_filters["season"] = season

        try:
            plan = Plan.objects.select_related("statement").get(**plan_filters)
        except Plan.DoesNotExist:
            return Response(
                {"detail": "Plan not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 🔹 BARCHA columnlarni OLDINDAN yuklaymiz (1 ta query)
        columns = StatementColumn.objects.all()
        column_map = {c.id: c for c in columns}

        context = {
            "lang": lang,
            "column_map": column_map,
        }

        # =====================================================
        # ✅ CASE 1: use_plant_plan = FALSE
        # =====================================================
        if not plan.statement.use_plant_plan:
            qs = (
                PlanItem.objects
                .filter(plan=plan)
                .select_related("column", "column__parent")
                .order_by("column__ordering")
            )

            serializer = ColumnPlanItemSerializer(
                qs,
                many=True,
                context=context
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        # =====================================================
        # ✅ CASE 2: use_plant_plan = TRUE
        # =====================================================
        qs = (
            PlantPlanItem.objects
            .filter(plant_plan__plan=plan)
            .select_related(
                "column",
                "column__parent",
                "plant_plan__plant",
            )
            .order_by("plant_plan__plant", "column__ordering")
        )

        grouped = defaultdict(list)

        for item in qs:
            grouped[item.plant_plan.plant].append(item)

        result = [
            {
                "plant_id": plant.id,
                "plant_name": plant.name,
                "items": items,
            }
            for plant, items in grouped.items()
        ]

        serializer = PlantPlanGroupSerializer(
            result,
            many=True,
            context=context
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
