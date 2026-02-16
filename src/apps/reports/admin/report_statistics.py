from django.urls import path
from django.contrib import admin
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
    list_display = ['id', 'created_at']

    # MUHIM: Bu model uchun changelist ni o'chirish
    def get_model_perms(self, request):
        return {'add': False, 'change': False, 'delete': False, 'view': True}

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Asosiy sahifa - statistikalar
            path('', self.admin_site.admin_view(self.statistics_view),
                 name='report_admin_stat_reportstatistics_changelist'),
            path('statistics/', self.admin_site.admin_view(self.statistics_view), name='report-statistics'),
            path('export/', self.admin_site.admin_view(self.export_excel), name='report-statistics-export'),
        ]
        return custom_urls + urls

    def statistics_view(self, request):
        filters = {
            "organization": request.GET.get("organization"),
            "statement": request.GET.get("statement"),
            "status": request.GET.get("status"),
            "deadline": request.GET.get("deadline"),
        }

        # Filterlardan bo'sh qiymatlarni olib tashlash
        filters = {k: v for k, v in filters.items() if v}

        stats_data = get_report_statistics(filters)

        # Unique organizatsiyalar va statementlar sonini hisoblash
        unique_orgs = set()
        unique_stmts = set()
        total_count = 0

        for row in stats_data:
            if row.get('organization__name'):
                unique_orgs.add(row['organization__name'])
            if row.get('statement__name_uz'):
                unique_stmts.add(row['statement__name_uz'])
            total_count += row.get('total', 0)

        # Eng ko'p hisobot
        max_report = 0
        if stats_data:
            max_report = max(row.get('total', 0) for row in stats_data)

        context = {
            "stats": stats_data,
            "organizations": Organization.objects.all(),
            "statements": Statement.objects.filter(is_used=True),
            "statuses": Report.StatusChoices.choices,
            "deadlines": Deadline.objects.all().select_related('statement'),
            "filters": filters,
            "total_count": total_count,
            "unique_orgs_count": len(unique_orgs),
            "unique_stmts_count": len(unique_stmts),
            "max_report": max_report,
            "title": "Hisobotlar statistikasi",
        }

        return render(request, "admin/reports/report_statistics.html", context)

    def export_excel(self, request):
        filters = {
            "organization": request.GET.get("organization"),
            "statement": request.GET.get("statement"),
            "status": request.GET.get("status"),
            "deadline": request.GET.get("deadline"),
        }

        # Filterlardan bo'sh qiymatlarni olib tashlash
        filters = {k: v for k, v in filters.items() if v}

        wb = export_statistics_excel(filters)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=report_statistics.xlsx"
        wb.save(response)
        return response

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True