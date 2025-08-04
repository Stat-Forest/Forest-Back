from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.reports.models import Plan, PlanItem
from apps.reports.serializers import (
    PlanSerializer,
    PlanListSerializer,
    PlanItemValueUpdateSerializer,
    PlanUpdateSerializer

)
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.permissions import CanCreatePlan
from apps.utils.translation import get_lang_code, get_translated_field


@extend_schema(tags=["Plan"])
class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.select_related('organization', 'statement')
    serializer_class = PlanSerializer
    permission_classes = [CanCreatePlan]


@extend_schema(tags=["Plan"])
class PlanRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Plan.objects.select_related('organization', 'statement')
    serializer_class = PlanSerializer
    # permission_classes = [CanCreatePlan]


@extend_schema(tags=["Plan"])
class PlanUpdateAPIView(generics.UpdateAPIView):
    queryset = Plan.objects.select_related('organization', 'statement')
    serializer_class = PlanUpdateSerializer
    # permission_classes = [CanCreatePlan]


@extend_schema(tags=["Plan"])
class PlanListAPIView(generics.ListAPIView):
    queryset = Plan.objects.select_related('organization', 'statement')
    serializer_class = PlanListSerializer
    filterset_fields = ['statement', 'organization', 'year']

    def get_queryset(self):
        user = self.request.user
        if user.organization is not None:
            return self.queryset.filter(organization_id=user.organization.pk)
        return self.queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang", "uz")
        context["lang"] = lang
        return context


@extend_schema(tags=["Plan"])
class PlanDeleteAPIView(generics.DestroyAPIView):
    queryset = Plan.objects.all()

    def delete(self, request, *args, **kwargs):
        try:
            return self.destroy(request, *args, **kwargs)
        except Exception as e:
            raise CustomExceptionError(detail={"error": str(e)})



