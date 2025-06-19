import django_filters
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend, filters

from apps.reports.models import Plant
from apps.base.views import CustomListAPIView
from apps.reports.serializers.plant_column import PlantSerializer


class PlantFilter(django_filters.FilterSet):
    parent = filters.ModelChoiceFilter(
        queryset=Plant.objects.filter(parent__isnull=True)
    )

    class Meta:
        model = Plant
        fields = ['parent']


@extend_schema(tags=["Plant"])
class PlantListAPIView(CustomListAPIView):
    serializer_class = PlantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PlantFilter

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            return Plant.objects.filter(parent_id=parent_id).prefetch_related("children", "parent")
        return Plant.objects.filter(parent__isnull=True).prefetch_related("children", "parent")

{
  "deadline": "c754ee0c-5d42-4364-a8f0-77329a5165ae",
  "report_items": [
    {
      "statement_column": "b7e05303-b027-411f-bb93-d27ce59d4023",
      "value": "60a41af5-49db-41ef-a222-27138d38ae67"
    },
   {
      "statement_column": "356f5e5a-511d-45b4-9c4d-174d54081402",
      "value": "10"
    },
    {
      "statement_column": "1586f4e2-a7e8-4a05-9620-db062704086f",
      "value": "10"
    },
    {
      "statement_column": "d6bfcd2b-07bf-40de-8576-d23c4d65e9f4",
      "value": "10"
    },
    {
      "statement_column": "018cfb27-4a97-4cd1-ae97-3b2d07e1f219",
      "value": "10"
    },
    {
      "statement_column": "f42f0464-2764-4451-ad87-469848fe7ef6",
      "value": "10"
    },
    {
      "statement_column": "31eb734f-42ec-4595-971a-e1e1d51a931f",
      "value": "10"
    },
    {
      "statement_column": "33152143-b650-4420-9c66-ecd85c70ced1",
      "value": "10"
    },
    {
      "statement_column": "c8873261-b4fd-4bcf-a3a4-bad78662ce55",
      "value": "10"
    },
    {
      "statement_column": "f0e63cc2-5550-48ff-b806-e64d6020e4b5",
      "value": "10"
    },
    {
      "statement_column": "899de5c2-9802-450b-abea-83816bbd9d98",
      "value": "10"
    },
    {
      "statement_column": "2d4c219f-a0d5-4585-8282-aba10eb8eada",
      "value": "10"
    },
    {
      "statement_column": "2af3596a-d202-4d30-931a-e700c924c2dd",
      "value": "10"
    },
    {
      "statement_column": "b07bba8e-86bd-4b2d-8d04-430dcfe599bc",
      "value": "10"
    },
    {
      "statement_column": "23f26fdd-c98e-458a-98ca-b0e095d874cc",
      "value": "10"
    },
    {
      "statement_column": "8603f63b-f157-466e-8cf6-0545c68a4401",
      "value": "10"
    },
    {
      "statement_column": "8708faf9-a432-45a2-8e51-8a1f6a4d82bb",
      "value": "10"
    },
    {
      "statement_column": "d77a8d8b-f46f-4fd0-9703-dc826a324679",
      "value": "10"
    },
    {
      "statement_column": "9ebf5ead-8966-48e1-94fa-2ed23584a966",
      "value": "10"
    }
  ]
}

{
  "deadline": "3f4d7946-145c-4c7b-afc9-f5d07b1aa113",
  "report_items": [
    {
      "statement_column": "1373e20f-58e7-4dac-a521-725137b658ff",
      "value": "142310a4-af61-45ba-85e3-a7ea84354255"
    },
    {
      "statement_column": "9019e8f3-3683-4c43-9138-5867bd3f48c2",
      "value": [
        {"plant_id": "17ac626e-d564-400a-a520-2dc5f50a0031", "value": "12.5"},
        {"plant_id": "47ada35f-abb8-4985-951d-da0763b8f088", "value": "8.0"},
        {"plant_id": "225eb944-3578-439b-8a20-e814a540d623", "value": "8.0"},
        {"plant_id": "6bae4d0d-d34f-4066-94a4-21bd7bf1eb74", "value": "8.0"}
      ]
    }
  ]
}
