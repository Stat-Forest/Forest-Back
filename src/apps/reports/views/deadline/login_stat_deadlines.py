# views.py
from django.db.models import Exists, OuterRef
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
        qs = (
            Deadline.objects
            .select_related("statement", "statement__parent")
            .prefetch_related("organizations")
            .distinct()
        )

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

        return qs.order_by("-submit_at", "-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        period_type = request.query_params.get("period_type")

        # ✅ submit_at bo'yicha dedupe
        all_deadlines = list(queryset)
        seen = set()
        unique_deadlines = []
        for deadline in all_deadlines:
            if deadline.submit_at not in seen:
                seen.add(deadline.submit_at)
                unique_deadlines.append(deadline)

        # Davr statistikasi — barcha qatorlar uchun bitta so'rov
        period_stats = build_period_stats(all_deadlines)

        # ✅ Pagination — count/next/previous saqlanadi
        page = self.paginate_queryset(unique_deadlines)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={
                    **self.get_serializer_context(),
                    "period_type": period_type,
                    "all_deadlines": all_deadlines,
                    "period_stats": period_stats,
                }
            )
            return self.get_paginated_response(serializer.data)

        # ✅ Pagination bo'lmasa oddiy response
        serializer = self.get_serializer(
            unique_deadlines,
            many=True,
            context={
                **self.get_serializer_context(),
                "period_type": period_type,
                "all_deadlines": all_deadlines,
                "period_stats": period_stats,
            }
        )
        return Response(serializer.data)