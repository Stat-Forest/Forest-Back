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

    actions = ["export_as_excel", "export_all_as_excel"]

    def user_organization(self, obj):
        if obj.user and obj.user.organization:
            return obj.user.organization.name_uz
        return "-"
    user_organization.short_description = "Organization"

    # -----------------------------------------
    #   📌 COMMON FUNCTION — Excel creator
    # -----------------------------------------
    def _create_excel_response(self, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = "History Export"

        # Header
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

        # Rows
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

        # Prepare response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=history_export.xlsx"
        wb.save(response)

        return response

    # -----------------------------------------
    #   📌 ACTION 1: Export selected rows
    # -----------------------------------------
    def export_as_excel(self, request, queryset):
        return self._create_excel_response(queryset)

    export_as_excel.short_description = "Export selected to Excel"

    # -----------------------------------------
    #   📌 ACTION 2: Export ALL rows
    # -----------------------------------------
    def export_all_as_excel(self, request, queryset):
        all_rows = HistoryActionJournal.objects.all()
        return self._create_excel_response(all_rows)

    export_all_as_excel.short_description = "Export ALL logs to Excel"

    # ---- permissions ----
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
