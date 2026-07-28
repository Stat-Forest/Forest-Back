from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.general.models import Organization
from apps.utils.services import RegionChoices
from apps.general.serializers.organization import OrganizationsByRegionResponseSerializer


class OrganizationsGroupedByRegionAPIView(APIView):
    """
    Respublika Jami -> Viloyatlar (soni bilan) -> Tashkilotlar
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Barcha organizationlar
        organizations = (
            Organization.objects
            .filter(region__isnull=False)
            .only("id", "name", "region")
            .order_by("region", "name")
        )

        total_count = organizations.count()

        # 2. Respublika Jami
        republic_data = {
            "label": "Respublika Jami",
            "count": total_count,
            "display": f"Respublika Jami — {total_count} ta"
        }

        # 3. Viloyatlar bo‘yicha guruhlash
        region_map = defaultdict(list)

        for org in organizations:
            region_map[org.region].append(org)

        regions_data = []

        for region_code, orgs in region_map.items():
            region_label = dict(RegionChoices.choices).get(region_code, region_code)
            count = len(orgs)

            regions_data.append({
                "region": region_label,
                "count": count,
                "display": f"{region_label} {count} ta",
                "organizations": orgs
            })

        # 4. Final response
        response_data = {
            "republic": republic_data,
            "regions": regions_data
        }

        serializer = OrganizationsByRegionResponseSerializer(response_data)
        return Response(serializer.data)

