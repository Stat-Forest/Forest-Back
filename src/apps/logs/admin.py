from django.urls import path
from django.shortcuts import redirect
from django.contrib import admin
from openpyxl import Workbook
from django.http import HttpResponse

from .models import HistoryActionJournal


@admin.register(HistoryActionJournal)
class HistoryActionJournalAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'user_organization',
        'action',
        'model_name',
        'object_repr',
        'change_message',
        'created_at',
    )

    actions = ["export_as_excel"]

    def user_organization(self, obj):
        if obj.user and obj.user.organization:
            return obj.user.organization.name_uz
        return "-"
    user_organization.short_description = "Organization"

    # -------- EXCEL CREATOR GENERAL FUNCTION ----------
    def _create_excel_response(self, rows, filename="history_export.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "History Export"

        columns = [
            "User",
            "Organization",
            "Action",
            "Model Name",
            "Object Repr",
            "Change Message",
            "Created At",
        ]
        ws.append(columns)

        for obj in rows:
            ws.append([
                obj.user.email if obj.user else "-",
                obj.user.organization.name_uz if (obj.user and obj.user.organization) else "-",
                obj.action,
                obj.model_name,
                obj.object_repr,
                obj.change_message,
                obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        wb.save(response)
        return response

    # -------- ACTION: Export SELECTED ----------
    def export_as_excel(self, request, queryset):
        return self._create_excel_response(queryset)
    export_as_excel.short_description = "Export selected to Excel"

    # -------- CUSTOM URL for Export ALL ----------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-all/",
                self.admin_site.admin_view(self.export_all_logs),
                name="history_export_all",
            ),
        ]
        return custom_urls + urls

    def export_all_logs(self, request):
        rows = HistoryActionJournal.objects.all()
        return self._create_excel_response(rows, filename="all_history_logs.xlsx")

    # -------- BUTTON IN ADMIN LIST PAGE ----------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["export_all_url"] = "export-all/"
        return super().changelist_view(request, extra_context=extra_context)
