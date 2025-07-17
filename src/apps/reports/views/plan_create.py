from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.reports.models import Plan, StatementColumn
from apps.reports.serializers import PlanSerializer, PlanListSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.permissions import CanCreatePlan

@extend_schema(tags=["Plan"])
class PlanCreateView(generics.CreateAPIView):
    queryset = Plan.objects.select_related('organization','statement')
    serializer_class = PlanSerializer
    permission_classes = [CanCreatePlan]



@extend_schema(tags=["Plan"])
class PlanListAPIView(generics.ListAPIView):
    queryset = Plan.objects.select_related('organization','statement')
    serializer_class = PlanListSerializer
    filterset_fields = ['statement', 'organization', 'year']

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if user.organization is not None:
            return queryset.filter(organization_id=user.organization.pk)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang")
        if not lang:
            lang = "uz"
        context["lang"] = lang
        return context