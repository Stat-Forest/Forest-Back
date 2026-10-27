# views.py
from django.core.cache import cache
from django.db.models import Exists, OuterRef
from django.utils.translation import get_language
from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.reports.models import Deadline, Report
from apps.reports.serializers.deadline import DeadlineReportListSerializer
from apps.reports.serializers.deadline.login_stat_deadline import build_period_stats
from rest_framework.permissions import AllowAny

MONTHLY_STATEMENTS = [
    "Dorivor yetishtirish",
    "O'rmon barpo qilish bo'limi",
    "Ko'chatxona va Niholxona Jami",
    "Tut Ko'chat va Tut Nihol"
]

YEARLY_STATEMENTS = [
    "O'rmon bilan qoplangan yerlar",
    "Yer o'zlashtirish"
]


@extend_schema(
    tags=["Deadlines"],
    parameters=[
        OpenApiParameter(
            name="period_type",
            type=OpenApiTypes.STR,
            required=False,
            description=(
                "monthly → Oylik hisobotlar uchun\n"
                "yearly → Yillik hisobotlar uchun"
            ),
            enum=["monthly", "yearly"]
        )
    ],
)
class DeadlineLoginStatListAPIView(generics.ListAPIView):
    serializer_class = DeadlineReportListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Deadline.objects.distinct()

        period_type = self.request.query_params.get("period_type")

        if period_type == "monthly":
            qs = qs.filter(statement__name_uz__in=MONTHLY_STATEMENTS)
        elif period_type == "yearly":
            qs = qs.filter(statement__name_uz__in=YEARLY_STATEMENTS)

        report_exists_qs = Report.objects.filter(
            deadline=OuterRef("pk"),
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )
        qs = qs.annotate(has_report=Exists(report_exists_qs)).filter(has_report=True)

        return qs

    LIST_CACHE_TTL = 300

    def list(self, request, *args, **kwargs):
        """
        Davrlar (submit_at) ro'yxati sahifalanadi; muddatlar va statistika
        faqat sahifadagi davrlar uchun yuklanadi. Ilgari barcha muddatlar
        tashkilotlari bilan (prod'da ~19 000 qator) har so'rovda yuklanardi.
        Ochiq (login sahifasi) endpoint — javob 5 daqiqa keshlanadi.
        """
        # Faqat ishlatiladigan parametrlar kalitga kiradi — notanish parametr bilan
        # keshni to'ldirib bo'lmaydi (audit C5)
        allowed = ('page', 'per_page', 'period_type')
        key_parts = "&".join(f"{k}={request.query_params.get(k, '')[:50]}" for k in allowed)
        cache_key = f"login_stat_deadlines:{get_language()}:{key_parts}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        base = self.get_queryset()
        period_type = request.query_params.get("period_type")

        periods = list(
            base.order_by("-submit_at").values_list("submit_at", flat=True).distinct()
        )
        page = self.paginate_queryset(periods)
        page_periods = page if page is not None else periods

        deadlines = list(
            base.filter(submit_at__in=page_periods)
            .select_related("statement", "statement__parent")
            .order_by("-submit_at", "-created_at")
        )

        # Har davr uchun bitta vakil qator (eng so'nggi yaratilgan muddat)
        seen = set()
        rows = []
        for deadline in deadlines:
            if deadline.submit_at not in seen:
                seen.add(deadline.submit_at)
                rows.append(deadline)

        serializer = self.get_serializer(
            rows,
            many=True,
            context={
                **self.get_serializer_context(),
                "period_type": period_type,
                "all_deadlines": deadlines,
                "period_stats": build_period_stats(deadlines),
            }
        )
        if page is not None:
            data = self.get_paginated_response(serializer.data).data
        else:
            data = serializer.data

        cache.set(cache_key, data, self.LIST_CACHE_TTL)
        return Response(data)
