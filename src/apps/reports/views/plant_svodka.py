from drf_spectacular.types import OpenApiTypes

from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.reports.models import Statement, Plant, Deadline
from apps.utils.translation import get_lang_code
from apps.reports.services.plant_svodka import build_plant_svodka
from apps.reports.serializers.plant.plant_svodka import PlantSvodkaQuerySerializer


@extend_schema(
    tags=["Plant-Reports"],
    request=None,
    responses={200: dict},
    parameters=[
        OpenApiParameter(
            "deadline",
            OpenApiTypes.UUID,
            OpenApiParameter.QUERY,
            required=True
        ),
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

    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        deadline_id = serializer.validated_data["deadline"]
        statement_id = serializer.validated_data["statement"]
        plant_id = serializer.validated_data.get("plant")

        deadline = Deadline.objects.filter(id=deadline_id).first()
        if not deadline:
            return Response({"detail": "Deadline not found"}, status=404)

        statement = Statement.objects.filter(id=statement_id).first()
        if not statement:
            return Response({"detail": "Statement not found"}, status=404)

        plant = None
        if plant_id:
            plant = Plant.objects.filter(id=plant_id).first()
            if not plant:
                return Response({"detail": "Plant not found"}, status=404)

        lang = serializer.validated_data.get("lang") or get_lang_code(request)

        data = build_plant_svodka(
            statement=statement,
            deadline=deadline,
            plant=plant,
            lang=lang
        )

        return Response(data)
