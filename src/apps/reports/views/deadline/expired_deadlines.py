from datetime import date

from django.db import models
from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters

from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline.expired_deadlines import (
    DeadlineExpiredSerializer
)
from apps.utils.services import PeriodChoices


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


@extend_schema(tags=["Deadlines"])
class DeadlineExpiredListAPIView(generics.ListAPIView):
    serializer_class = DeadlineExpiredSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DeadlineExpiredFilter

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        RAHBARIYAT = "rahbariyat", "Rahbariyat"
        BOLIM_ADMIN = "bolim_admin", "Bo‘lim Admin"
        TASHKILOT_RAHBARI = "tashkilot_rahbari", "Tashkilot rahbari"
        TASHKILOT_HODIMI = "tashkilot_hodimi", "Tashkilot hodimi"
        HUDUDIY_BOSHQARMA = "hududiy_boshqarma", "Hududiy boshqarma"

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Deadline.objects
            .filter(deadline_at__lt=date.today())
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .order_by("deadline_at")
        )

        # SUPER_ADMIN — hammasi
        if user.role == self.Role.SUPER_ADMIN:
            return queryset

        # BOLIM_ADMIN — faqat o‘z statementlari
        if user.role == self.Role.BOLIM_ADMIN:
            return queryset.filter(statement=user.statement)

        # TASHKILOT_RAHBARI / TASHKILOT_HODIMI — faqat user.organization ichida bo‘lgan deadline
        if user.role in {self.Role.TASHKILOT_RAHBARI, self.Role.TASHKILOT_HODIMI}:
            return queryset.filter(organizations=user.organization)

        # Default: hech narsa qaytmasin
        return queryset.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = request.user

        valid_deadlines = []

        for deadline in queryset:
            # TASHKILOT_RAHBARI / HODIMI uchun: shu deadline ichida user.organization borligini tekshirish
            if user.role in {self.Role.TASHKILOT_RAHBARI, self.Role.TASHKILOT_HODIMI}:
                if user.organization not in deadline.organizations.all():
                    continue  # bu deadline ularga ko‘rinmaydi

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
