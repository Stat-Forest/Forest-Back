from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.reports.models import Plan, PlanItem
from apps.reports.serializers import (
    PlanSerializer,
    PlanListSerializer,
    PlanItemValueUpdateSerializer
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


@extend_schema(tags=["Plan"])
class PlanItemBulkUpdateView(generics.GenericAPIView):
    serializer_class = PlanItemValueUpdateSerializer
    permission_classes = [CanCreatePlan]
    queryset = Plan.objects.all()

    def put(self, request, *args, **kwargs):
        plan = self.get_object()
        plan_items_data = request.data.get("plan_items", [])
        context = {"plan": plan}

        errors = []
        updated = 0

        with transaction.atomic():
            for item_data in plan_items_data:
                # Remove column_name if present in input
                item_data.pop("column_name", None)

                serializer = self.get_serializer(data=item_data, context=context)
                if serializer.is_valid():
                    column_id = serializer.validated_data["column"]
                    value = serializer.validated_data["value"]

                    try:
                        plan_item = PlanItem.objects.get(plan=plan, column_id=column_id)
                        plan_item.plan_value = value
                        plan_item.save()
                        updated += 1
                    except PlanItem.DoesNotExist:
                        errors.append({
                            "column_id": column_id,
                            "column_name": None,
                            "value": value,
                            "errors": {"column_id": [_("Plan item does not exist.")]}
                        })
                else:
                    # Extract column_id and column_name for error info
                    column_id = item_data.get("column_id")
                    column_name = None

                    if column_id:
                        try:
                            column_obj = PlanItem.objects.get(plan=plan, column_id=column_id).column
                            lang = get_lang_code(context)
                            column_name = get_translated_field(column_obj, "name", lang)
                        except PlanItem.DoesNotExist:
                            pass

                    errors.append({
                        "column_id": column_id,
                        "column_name": column_name,
                        "value": item_data.get("value"),
                        "errors": serializer.errors
                    })

        return Response({
            "updated": updated,
            "errors": errors
        }, status=status.HTTP_200_OK if updated else status.HTTP_400_BAD_REQUEST)
