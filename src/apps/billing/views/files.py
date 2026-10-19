"""Shartnoma fayllari: ro'yxat (?contract=), multipart yuklash, o'chirish."""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.billing.models import ContractFile, ContractHistory
from apps.billing.permissions import BillingPIIReadOrWrite
from apps.billing.scope import NOT_ASSIGNED_MESSAGE, can_write_xojalik, scope_queryset
from apps.billing.serializers import ContractFileSerializer
from apps.billing.services import history
from apps.logs.drf_mixins import DRFHistoryMixin


@extend_schema(tags=["Billing"])
class ContractFileViewSet(
    DRFHistoryMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [BillingPIIReadOrWrite]  # fayllar (pasport/shartnoma skanlari) — faqat PII rollari
    serializer_class = ContractFileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["contract"]
    queryset = ContractFile.objects.select_related("contract", "uploaded_by").order_by("-created_at")

    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request.user, "contract__xojalik_id")

    def perform_create(self, serializer):
        user = self.request.user
        if not can_write_xojalik(user, serializer.validated_data["contract"].xojalik_id):
            raise ValidationError({"contract": [NOT_ASSIGNED_MESSAGE]})
        obj = serializer.save(uploaded_by=user, created_by=user, updated_by=user)
        obj._history_user = user
        history.record(obj.contract, user, ContractHistory.Reason.FILE_ADDED, {"file": serializer.data.get("file_name")})
        return obj

    def perform_destroy(self, instance):
        contract, name = instance.contract, instance.file.name.rsplit("/", 1)[-1]
        stored_file = instance.file
        super().perform_destroy(instance)
        stored_file.delete(save=False)
        history.record(contract, self.request.user, ContractHistory.Reason.FILE_DELETED, {"file": name})
