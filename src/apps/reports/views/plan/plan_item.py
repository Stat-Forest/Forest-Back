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
from apps.reports.serializers.plan import FlatPlanItemSerializer


@extend_schema(
    tags=["PlanItem"],
    parameters=[
        OpenApiParameter("organization", OpenApiTypes.UUID, required=True),
        OpenApiParameter("statement", OpenApiTypes.UUID, required=True),
        OpenApiParameter("year", OpenApiTypes.INT, required=True),
        OpenApiParameter("season", OpenApiTypes.STR),
        OpenApiParameter("plant", OpenApiTypes.UUID),
        OpenApiParameter("column", OpenApiTypes.UUID),
        OpenApiParameter("lang", OpenApiTypes.STR),
    ]
)
class PlanItemDetailAPIView(APIView):

    def get(self, request):
        # ===============================
        # ✅ REQUIRED PARAM CHECK
        # ===============================
        for param in ("organization", "statement", "year"):
            if not request.query_params.get(param):
                return Response(
                    {"detail": f"{param} query param is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ===============================
        # ✅ SAFE CAST
        # ===============================
        try:
            year = int(request.query_params["year"])
        except ValueError:
            return Response(
                {"detail": "year must be integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        lang = request.query_params.get("lang", "uz")

        plan_filters = {
            "organization_id": request.query_params["organization"],
            "statement_id": request.query_params["statement"],
            "year": year,
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

        # ===============================
        # ✅ COLUMN CACHE
        # ===============================
        columns = StatementColumn.objects.all()
        column_map = {c.id: c for c in columns}

        context = {
            "lang": lang,
            "column_map": column_map,
        }

        column_id = request.query_params.get("column")
        plant_id = request.query_params.get("plant")

        result = []

        # =====================================================
        # ✅ CASE 1: use_plant_plan = FALSE
        # =====================================================
        if not plan.statement.use_plant_plan:
            qs = (
                PlanItem.objects
                .filter(plan=plan)
                .select_related("column", "column__parent")
            )

            if column_id:
                qs = qs.filter(column_id=column_id)

            for item in qs:
                result.append({
                    "plant_id": None,
                    "plant_name": None,
                    "column": item.column,
                    "plan_value": item.plan_value,
                })

        # =====================================================
        # ✅ CASE 2: use_plant_plan = TRUE
        # =====================================================
        else:
            qs = (
                PlantPlanItem.objects
                .filter(plant_plan__plan=plan)
                .select_related(
                    "column",
                    "column__parent",
                    "plant_plan__plant",
                )
            )

            if plant_id:
                qs = qs.filter(plant_plan__plant_id=plant_id)

            if column_id:
                qs = qs.filter(column_id=column_id)

            for item in qs:
                result.append({
                    "plant_id": item.plant_plan.plant.id,
                    "plant_name": item.plant_plan.plant.name,
                    "column": item.column,
                    "plan_value": item.plan_value,
                })

        serializer = FlatPlanItemSerializer(
            result,
            many=True,
            context=context
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
