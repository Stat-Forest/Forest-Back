from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse

from apps.general.models import Organization
from apps.reports.models import Statement, Report, Deadline
from apps.reports.models.report_statistics import ReportStatistics
from apps.reports.services.report_statistics import (
    get_report_statistics,
    export_statistics_excel
)


@admin.register(ReportStatistics)
class ReportStatisticsAdmin(admin.ModelAdmin):

    def get_urls(self):
        urls = super().get_urls()
        return [
            path("", self.admin_site.admin_view(self.statistics_view), name="report-statistics"),
            path("export/", self.admin_site.admin_view(self.export_excel), name="report-statistics-export"),
        ] + urls

    def statistics_view(self, request):

        filters = {
            "organization": request.GET.get("organization"),
            "statement": request.GET.get("statement"),
            "status": request.GET.get("status"),
            "deadline": request.GET.get("deadline"),
        }

        context = {
            "stats": get_report_statistics(filters),
            "organizations": Organization.objects.all(),
            "statements": Statement.objects.all(),
            "statuses": Report.StatusChoices.choices,
            "deadlines": Deadline.objects.all(),
            "filters": filters,
        }

        return render(request, "admin/reports/report_statistics.html", context)

    def export_excel(self, request):

        filters = {
            "organization": request.GET.get("organization"),
            "statement": request.GET.get("statement"),
            "status": request.GET.get("status"),
            "deadline": request.GET.get("deadline"),
        }

        wb = export_statistics_excel(filters)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=report_statistics.xlsx"
        wb.save(response)
        return response

    def has_add_permission(self, r): return False
    def has_change_permission(self, r, o=None): return False
    def has_delete_permission(self, r, o=None): return False