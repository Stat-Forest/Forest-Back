# Third-party imports
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

# Local imports
from apps.reports.models import Plan
from apps.reports.serializers.plan import PlanSerializer

# -----------------------------------------------------------------------------
# Plan Update API
# -----------------------------------------------------------------------------
@extend_schema(tags=["Plan"])
class PlanUpdateView(generics.UpdateAPIView):
    """
    Update an existing Plan object.

    Notes:
    - The 'statement' field cannot be updated.
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def update(self, request, *args, **kwargs):
        """
        Override update to exclude 'statement' field from being modified.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Prevent 'statement' field from being updated
        data = request.data.copy()
        data.pop("statement", None)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------------------------------------------------------
# Plan Retrieve API
# -----------------------------------------------------------------------------
@extend_schema(tags=["Plan"])
class PlanRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve a single Plan object by ID.
    Supports only GET method.
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
