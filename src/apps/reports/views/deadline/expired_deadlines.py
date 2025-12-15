from datetime import date
from rest_framework import generics
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
        today = date.today()

        deadlines = (
            Deadline.objects
            .filter(deadline_at__lt=today)
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .order_by("deadline_at")
        )

        valid_deadlines = []

        for deadline in deadlines:
            valid_organizations = []

            for org in deadline.organizations.all():
                # FAQAT organization + deadline orqali tekshiramiz
                report_exists = Report.objects.filter(
                    organization=org,
                    deadline=deadline
                ).exists()

                # Agar report YO‘Q bo‘lsa → expired
                if not report_exists:
                    valid_organizations.append(org)

            # Agar kamida 1 ta organization qolsa → deadline qaytadi
            if valid_organizations :
                deadline._filtered_organizations = valid_organizations
                valid_deadlines.append(deadline)

        return valid_deadlines