from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.reports.models import Statement
from apps.reports.serializers.statement.appendices import StatementAppendicesQuerySerializer
from apps.reports.services.statement_appendices import build_appendices_payload
from apps.utils.translation import get_lang_code


@extend_schema(
    tags=["Statements"],
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
            name="lang",
            type=OpenApiTypes.STR,
            required=False,
            location=OpenApiParameter.QUERY,
            description="Language code (uz or ru)",
        ),
    ],
)
class StatementAppendicesAPIView(GenericAPIView):
    serializer_class = StatementAppendicesQuerySerializer
    queryset = Statement.objects.none()

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        statement_id = serializer.validated_data["statement"]
        lang = serializer.validated_data.get("lang") or get_lang_code(request)

        statement = Statement.objects.filter(id=statement_id).first()
        if not statement:
            return Response({"detail": "Statement not found"}, status=404)

        payload = build_appendices_payload(statement, lang)
        return Response(payload)
