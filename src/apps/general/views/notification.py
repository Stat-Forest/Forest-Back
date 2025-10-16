from rest_framework import generics
from django.utils.timezone import now
from apps.general.models import Notification
from apps.general.serializers import NotificationListSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    tags=["Notification"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Tilni tanlang: uz yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
        ),
    ],
)
class NotificationListCreateAPIView(generics.ListAPIView):
    serializer_class = NotificationListSerializer

    def get_queryset(self):
        today = now().date()
        return Notification.objects.filter(date=today)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context
