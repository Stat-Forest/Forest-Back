# Standard library
from django.utils.translation import gettext_lazy as _
from django.db.models import Prefetch
from django.db import transaction, IntegrityError
# Third-party
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from django_filters.rest_framework import DjangoFilterBackend
# Local apps
from apps.reports.serializers.plan import (
    PlanSerializer,
    PlanListSerializer,
)
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.permissions import CanCreatePlan,CanManagePlan
from apps.logs.drf_mixins import DRFHistoryMixin

from apps.reports.models import Plan, PlanItem, PlantPlan, PlantPlanItem,StatementColumn
from apps.users.models.users import CustomUser



# =============================================================================
# PLAN CREATE
# =============================================================================
@extend_schema(tags=["Plan"])
class PlanCreateView(DRFHistoryMixin, generics.CreateAPIView):
    """
    CREATE PLAN

    - season OPTIONAL
    - use_plant_plan = False -> plan_items
    - use_plant_plan = True  -> plants

    Response har doim PlanSerializer formatida
    """

    serializer_class = PlanSerializer
    queryset = Plan.objects.select_related("organization", "statement")
    permission_classes = [CanCreatePlan,CanManagePlan]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                plan = serializer.save()
        except IntegrityError:
            # DB-level unique constraint
            raise CustomExceptionError(
                400,
                {
                    "detail": _(
                        "Plan already exists for this organization, statement, year and season"
                    )
                }
            )

        output_serializer = PlanSerializer(
            plan,
            context={
                "request": request,
                "lang": request.query_params.get("lang", "uz"),
            },
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


# =============================================================================
# PLAN RETRIEVE
# =============================================================================
@extend_schema(tags=["Plan"])
class PlanRetrieveAPIView(generics.RetrieveAPIView):
    queryset = (
        Plan.objects
        .select_related("organization", "statement")
        .prefetch_related(
            Prefetch(
                "plan_items",
                queryset=PlanItem.objects.select_related(
                    "column",
                    "column__parent",
                    "column__parent__parent",
                )
            ),
            Prefetch(
                "plant_plans",
                queryset=PlantPlan.objects
                .select_related("plant")
                .prefetch_related(
                    Prefetch(
                        "items",
                        queryset=PlantPlanItem.objects.select_related(
                            "column",
                            "column__parent",
                            "column__parent__parent",
                        )
                    )
                )
            ),
            # 🔥 MUHIM
            Prefetch(
                "statement__columns",
                queryset=StatementColumn.objects.select_related(
                    "parent",
                    "parent__parent",
                )
            )
        )
    )
    serializer_class = PlanSerializer


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        return context




# =============================================================================
# PLAN LIST
# =============================================================================
@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Language: uz (default) or ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
        ),
        OpenApiParameter(
            name="season",
            description="Season filter (optional)",
            required=False,
            type=OpenApiTypes.STR,
        ),
    ],
)
class PlanListAPIView(generics.ListAPIView):
    serializer_class = PlanListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["statement", "organization", "year", "season"]

    queryset = (
        Plan.objects
        .select_related("organization", "statement")
        .prefetch_related(
            # PLAN ITEMS → COLUMN → PARENTS
            Prefetch(
                "plan_items",
                queryset=PlanItem.objects.select_related(
                    "column",
                    "column__parent",
                    "column__parent__parent",
                ),
            ),
            # PLANT PLANS → PLANT → ITEMS → COLUMN → PARENTS
            Prefetch(
                "plant_plans",
                queryset=PlantPlan.objects
                .select_related("plant")
                .prefetch_related(
                    Prefetch(
                        "items",
                        queryset=PlantPlanItem.objects.select_related(
                            "column",
                            "column__parent",
                            "column__parent__parent",
                        ),
                    )
                ),
            ),
        )
    )

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # BOLIM_ADMIN
        if (
                user.role == CustomUser.Role.BOLIM_ADMIN
                and user.statement
        ):
            qs = qs.filter(statement__parent=user.statement)

        # HUDUDIY_BOSHQARMA
        elif user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            qs = qs.filter(
                organization__in=user.region_user_orgs.all()
            )

        # TASHKILOT
        elif (
                user.role in (
                CustomUser.Role.TASHKILOT_HODIMI,
                CustomUser.Role.TASHKILOT_RAHBARI,
        )
                and user.organization
        ):
            qs = qs.filter(organization=user.organization)

        return qs.order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "uz")
        return context


# =============================================================================
# PLAN DELETE
# =============================================================================
@extend_schema(tags=["Plan"])
class PlanDeleteAPIView(DRFHistoryMixin, generics.DestroyAPIView):
    queryset = Plan.objects.all()
    permission_classes = [CanManagePlan,]

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            raise CustomExceptionError(
                status_code=400,
                detail={"error": str(e)}
            )
