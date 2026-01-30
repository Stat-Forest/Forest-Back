from datetime import date

from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters

from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline.expired_deadlines import DeadlineExpiredSerializer
from apps.utils.services import PeriodChoices
from apps.users.models import CustomUser


class DeadlineExpiredFilter(FilterSet):
    statement = filters.UUIDFilter(field_name="statement_id")
    deadline_at = filters.DateFilter(field_name="deadline_at")
    organizations = filters.UUIDFilter(field_name="organizations__id")

    period = filters.ChoiceFilter(
        choices=PeriodChoices.choices,
        method="filter_by_period"
    )

    class Meta:
        model = Deadline
        fields = ["statement", "deadline_at", "organizations", "period"]

    def filter_by_period(self, queryset, name, value):
        if value == PeriodChoices.KUNLIK:
            return queryset.filter(submit_at__regex=r'^\d{4}-\d{2}-\d{2}$')
        if value == PeriodChoices.HAFTALIK:
            return queryset.filter(submit_at__contains='HAFTALIK')
        if value == PeriodChoices.OYLIK:
            return queryset.filter(submit_at__regex=r'^\d{4}-\d{2}$')
        if value == PeriodChoices.CHORAKLIK:
            return queryset.filter(submit_at__contains='CHORAK')
        if value == PeriodChoices.YILLIK:
            return queryset.filter(submit_at__regex=r'^\d{4}$')
        return queryset


@extend_schema(
    tags=["Deadlines"],
    parameters=[
        OpenApiParameter(
            name="statement",
            description="Statement UUID",
            required=False,
            type=OpenApiTypes.UUID
        ),
        OpenApiParameter(
            name="deadline_at",
            description="Deadline date (YYYY-MM-DD)",
            required=False,
            type=OpenApiTypes.DATE
        ),
        OpenApiParameter(
            name="organizations",
            description="Organization UUID",
            required=False,
            type=OpenApiTypes.UUID
        ),
        OpenApiParameter(
            name="period",
            description="Period: daily, weekly, monthly, quarterly, yearly",
            required=False,
            type=OpenApiTypes.STR,
            enum=[c[0] for c in PeriodChoices.choices]
        ),
    ]
)
class DeadlineExpiredListAPIView(generics.ListAPIView):
    serializer_class = DeadlineExpiredSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DeadlineExpiredFilter

    def get_queryset(self):
        user: CustomUser = self.request.user

        queryset = (
            Deadline.objects
            .filter(deadline_at__lt=date.today())
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .order_by("deadline_at")
        )

        # SUPER_ADMIN — hammasi
        if user.role == CustomUser.Role.SUPER_ADMIN:
            return queryset

        # BOLIM_ADMIN — faqat o‘z statement parentiga teng bo‘lgan deadlinelar
        if user.role == CustomUser.Role.BOLIM_ADMIN and user.statement:
            return queryset.filter(statement__parent=user.statement)

        # TASHKILOT_RAHBARI / TASHKILOT_HODIMI — faqat user.organization ichida bo‘lgan deadline
        if user.role in {CustomUser.Role.TASHKILOT_RAHBARI, CustomUser.Role.TASHKILOT_HODIMI}:
            if user.organization:
                return queryset.filter(organizations=user.organization)
            else:
                return queryset.none()

        # Default: hech narsa qaytmasin
        return queryset.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user: CustomUser = request.user

        valid_deadlines = []

        for deadline in queryset:
            # TASHKILOT_RAHBARI / HODIMI uchun: shu deadline ichida user.organization borligini tekshirish
            if user.role in {CustomUser.Role.TASHKILOT_RAHBARI, CustomUser.Role.TASHKILOT_HODIMI}:
                if not user.organization or user.organization not in deadline.organizations.all():
                    continue

            valid_organizations = []

            for org in deadline.organizations.all():
                report_exists = Report.objects.filter(
                    organization=org,
                    deadline=deadline,
                    status=Report.StatusChoices.ACCEPTED,
                ).exists()

                if not report_exists:
                    valid_organizations.append(org)

            if valid_organizations:
                deadline._filtered_organizations = valid_organizations
                valid_deadlines.append(deadline)

        serializer = self.get_serializer(valid_deadlines, many=True)
        return Response(serializer.data)
