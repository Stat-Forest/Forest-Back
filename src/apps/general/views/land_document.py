from rest_framework import generics, filters
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from apps.general.models.land_document import LandDocument
from apps.general.permissions import allowed_organization_for_create, scope_by_organization
from apps.general.serializers.land_document import LandDocumentSerializer
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Land document"])
class LandDocumentListCreateView(DRFHistoryMixin, generics.ListCreateAPIView):
    """
    API endpoint for Land Documents.

    GET:
        Foydalanuvchi doirasidagi yer hujjatlari (scope_by_organization):
        tashkilot xodimi/rahbari — o'z tashkiloti, hududiy boshqarma — o'z
        hududi, bo'lim admin / rahbariyat / super admin — hammasi.

    POST:
        Tashkilot xodimi/rahbari faqat o'z tashkiloti nomidan yaratadi
        (yuborilgan `organization` e'tiborga olinmaydi), hududiy boshqarma —
        o'z hududidagi tashkilot nomidan.
    """

    serializer_class = LandDocumentSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ["name"]
    filterset_fields = ["organization"]
    ordering_fields = ["date", "created_at"]

    def get_queryset(self):
        # Ilgari butun ro'yxat bitta cache kalitida turardi — har kim hammani
        # ko'rardi. Endi rol bo'yicha cheklanadi, cache ishlatilmaydi.
        queryset = LandDocument.objects.select_related("organization").order_by("-date")
        return scope_by_organization(queryset, self.request.user)

    def perform_create(self, serializer):
        organization = allowed_organization_for_create(
            self.request.user, serializer.validated_data.get("organization")
        )
        if organization is None:
            raise PermissionDenied("Bu tashkilot nomidan hujjat yaratishga ruxsat yo'q.")
        obj = serializer.save(organization=organization)
        obj._history_user = self.request.user
        obj.save(update_fields=[])
        return obj

    def get_serializer_context(self):
        """
        Adds request context for absolute file URL generation.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
