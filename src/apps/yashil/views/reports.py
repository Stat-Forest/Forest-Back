"""Hisobot reestri API (TZ §14): reestr, jami, filtr lug'atlari."""
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.yashil.api import CabinetMixin, HasCabinet, IsAuthenticated, invalid_format
from apps.yashil.services import registry


class _ReportBase(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)

    def filters(self, request) -> dict:
        try:
            return registry.parse_filters(request.query_params)
        except registry.RegistryFilterError as exc:
            raise invalid_format(str(exc), exc.field)


class RegistryPagination(CustomPageNumberPagination):
    page_size = 50
    max_page_size = 200


class RegistryView(_ReportBase):
    """GET reports/registry/ — qator = buyurtma pozitsiyasi, sahifalangan."""

    def get(self, request):
        f = self.filters(request)
        qs = registry.registry_queryset(self.cabinet, self.is_admin, f)
        paginator = RegistryPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        start = (paginator.page.number - 1) * paginator.page.paginator.per_page + 1
        response = paginator.get_paginated_response(registry.row_dicts(page, start_no=start))
        response.data["filters_label"] = registry.filters_label(f)
        return response


class RegistrySummaryView(_ReportBase):
    """GET reports/registry/summary/ — unikal buyurtmalar, pozitsiya/birlik jami, holatlar."""

    def get(self, request):
        f = self.filters(request)
        qs = registry.apply_filters(registry.base_queryset(self.cabinet, self.is_admin), f)
        data = registry.summary(qs)
        data["filters_label"] = registry.filters_label(f)
        return Response(data)


class ReportFiltersView(_ReportBase):
    """GET reports/filters/ — kabinet ko'lamidagi lug'atlar."""

    def get(self, request):
        return Response(registry.filter_dictionaries(self.cabinet, self.is_admin))
