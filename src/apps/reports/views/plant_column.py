import django_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django_filters.rest_framework import DjangoFilterBackend, filters

from apps.reports.models import Plant
from apps.base.views import CustomListAPIView
from apps.reports.serializers.plant import PlantSerializer


class PlantFilter(django_filters.FilterSet):
    parent = filters.ModelChoiceFilter(
        queryset=Plant.objects.filter(parent__isnull=True)
    )

    class Meta:
        model = Plant
        fields = ['parent']


@extend_schema(
    tags=["Plant"],
    parameters=[
        OpenApiParameter(name="lang", description="Language: uz, ru", required=False, type=str),
    ]
)
class PlantListAPIView(CustomListAPIView):
    serializer_class = PlantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PlantFilter

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            return Plant.objects.filter(parent_id=parent_id).prefetch_related("children", "parent")
        return Plant.objects.filter(parent__isnull=True).prefetch_related("children", "parent")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang")
        return context