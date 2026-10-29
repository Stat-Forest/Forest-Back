"""Hisobot reestri API (TZ §14): reestr, jami, filtr lug'atlari."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.yashil.api import CabinetMixin, HasCabinet, IsAuthenticated, YashilError, invalid_format, not_found
from apps.yashil.models import ExportJob
from apps.yashil.serializers_stock import relative_signed_url
from apps.yashil.services import exports, registry, stats


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


# ----------------------------------------------------------------------------- eksport (TZ §14.2)
def export_payload(job: ExportJob) -> dict:
    done = job.status == ExportJob.Status.DONE and bool(job.file)
    return {
        "id": str(job.id), "kind": job.kind, "format": job.format, "status": job.status, "row_count": job.row_count,
        "filters": job.filters, "error": job.error if job.status == ExportJob.Status.FAILED else "",
        "created_at": job.created_at.isoformat(), "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "url": relative_signed_url(job.file) if done else None,
        "filename": f"yashil-{job.kind}-{job.created_at:%Y%m%d-%H%M}.{job.format}" if done else None,
    }


class ExportCreateView(_ReportBase):
    """POST reports/exports/ {kind, format, filters} — kichik: 200 done; katta: 202 queued. GET — o'z vazifalari."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "export"

    def get(self, request):
        qs = ExportJob.objects.filter(requested_by=request.user).order_by("-created_at")[:20]
        return Response({"results": [export_payload(j) for j in qs]})

    def post(self, request):
        d = request.data if isinstance(request.data, dict) else {}
        filters = d.get("filters") or {}
        if not isinstance(filters, dict):
            raise invalid_format("filters лугʻат бўлиши керак", "filters")
        try:
            job = exports.create_job(request.user, self.cabinet, self.is_admin, kind=str(d.get("kind") or ""),
                                     fmt=str(d.get("format") or ""), filters=filters)
        except exports.ExportError as exc:
            raise YashilError(exc.message, error_code=exc.code, field=exc.field, status_code=exc.status)
        code = status.HTTP_202_ACCEPTED if job.status in ExportJob.ACTIVE_STATUSES else status.HTTP_200_OK
        return Response(export_payload(job), status=code)


class ExportDetailView(_ReportBase):
    def get(self, request, job_id):
        job = ExportJob.objects.filter(pk=job_id, requested_by=request.user).first()
        if job is None:
            raise not_found()
        return Response(export_payload(job))


# ----------------------------------------------------------------------------- statistika (TZ §15)
class StatsCardsView(_ReportBase):
    def get(self, request):
        return Response(stats.cards(self.cabinet, self.is_admin, self.filters(request)))


class StatsSeedlingsView(_ReportBase):
    def get(self, request):
        return Response(stats.seedlings(self.cabinet, self.is_admin, self.filters(request)))


class StatsOrganizationsView(_ReportBase):
    def get(self, request):
        f = self.filters(request)
        return Response({"results": stats.organizations(self.cabinet, self.is_admin, f), "filters_label": registry.filters_label(f)})
