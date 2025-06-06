from rest_framework import generics

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apps.reports.models import Plan, Report
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.reports.serializers.delete_plan import PlanDeleteSerializer
from apps.reports.serializers.update_plan import PlanUpdateSerializer


@extend_schema(tags=["Plan"])
class PlanUpdateAPIView(generics.UpdateAPIView):
    queryset = Plan.objects.select_related('organization', 'column')
    serializer_class = PlanUpdateSerializer
    lookup_field = "id"

    def get(self, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


@extend_schema(tags=["Plan"])
class PlanDeleteAPIView(generics.DestroyAPIView):
    queryset = Plan.objects.select_related("organization", "statement", "column")
    serializer_class = PlanDeleteSerializer
    lookup_field = "id"

    def get(self, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        if Report.objects.filter(
            statement=instance.statement,
            organization=instance.organization,
            report_items__statement_column_id=instance.column_id
        ).exists():
            raise CustomExceptionError(code=400, detail="Cannot delete Plan because related Reports exist. Delete the Reports first.")

        instance.delete()