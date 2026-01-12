from drf_spectacular.types import OpenApiTypes

from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.reports.models import Statement, Plant
from apps.utils.translation import get_lang_code
from apps.reports.services.plant_svodka import build_plant_svodka
from apps.reports.serializers.plant.plant_svodka import PlantSvodkaQuerySerializer


@extend_schema(
    tags=["Plant-Reports"],
    request=None,
    responses={200: dict},
    parameters=[
        OpenApiParameter(
            name="statement",
            type=OpenApiTypes.UUID,
            required=True,
            location=OpenApiParameter.QUERY,
            description="Statement ID (UUID)",
        ),
        OpenApiParameter(
            name="plant",
            type=OpenApiTypes.UUID,
            required=False,
            location=OpenApiParameter.QUERY,
            description="Optional Plant ID (UUID)",
        ),
        OpenApiParameter(
            name="lang",
            type=OpenApiTypes.STR,
            required=False,
            location=OpenApiParameter.QUERY,
            description="Language code (uz or ru)",
        ),
    ],
)
class PlantSvodkaAPIView(GenericAPIView):
    serializer_class = PlantSvodkaQuerySerializer
    queryset = Statement.objects.none()

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        statement_id = serializer.validated_data["statement"]
        plant_id = serializer.validated_data.get("plant")

        statement = Statement.objects.filter(id=statement_id).first()
        if not statement:
            return Response({"detail": "Statement not found"}, status=404)

        plant = None
        if plant_id:
            plant = Plant.objects.filter(id=plant_id).first()
            if not plant:
                return Response({"detail": "Plant not found"}, status=404)

        # Resolve language: serializer value has priority; then query/header via helper
        lang = serializer.validated_data.get("lang") or get_lang_code(request)

        include_empty = plant is None
        data = build_plant_svodka(statement, plant, include_empty=include_empty, lang=lang)
        return Response(data)
