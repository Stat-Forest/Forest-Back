from datetime import date
from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters

from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline.expired_deadlines import (
    DeadlineExpiredSerializer
)


class DeadlineExpiredFilter(FilterSet):
    statement = filters.NumberFilter(field_name="statement_id")
    submit_at = filters.CharFilter(field_name="submit_at", lookup_expr="exact")
    deadline_at = filters.DateFilter(field_name="deadline_at", lookup_expr="exact")
    organizations = filters.NumberFilter(field_name="organizations__id")

    class Meta:
        model = Deadline
        fields = ["statement", "submit_at", "deadline_at", "organizations"]


@extend_schema(tags=["Deadlines"])
class DeadlineExpiredListAPIView(generics.ListAPIView):
    serializer_class = DeadlineExpiredSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DeadlineExpiredFilter

    def get_queryset(self):
        return (
            Deadline.objects
            .filter(deadline_at__lt=date.today())
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .order_by("deadline_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        valid_deadlines = []

        for deadline in queryset:
            valid_organizations = []

            for org in deadline.organizations.all():
                report_exists = Report.objects.filter(
                    organization=org,
                    deadline=deadline
                ).exists()

                if not report_exists:
                    valid_organizations.append(org)

            if valid_organizations:
                deadline._filtered_organizations = valid_organizations
                valid_deadlines.append(deadline)

        serializer = self.get_serializer(
            valid_deadlines,
            many=True
        )
        return Response(serializer.data)
