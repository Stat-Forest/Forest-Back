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

    actions = ["export_as_excel"]  # <-- Excel export action

    def user_organization(self, obj):
        if obj.user and obj.user.organization:
            return obj.user.organization.name_uz
        return "-"
    user_organization.short_description = "Organization"

    # ============================
    #   📌 EXCEL EXPORT FUNCTION
    # ============================
    def export_as_excel(self, request, queryset):
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
        for obj in queryset:
            row = [
                obj.user.full_name if obj.user else "-",
                obj.user.organization.name_uz if (obj.user and obj.user.organization) else "-",
                obj.action,
                obj.model_name,
                obj.object_repr,
                obj.change_message,
                obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
            ws.append(row)

        # Response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename=history_export.xlsx'
        wb.save(response)

        return response

    export_as_excel.short_description = "Export selected to Excel"

    # ---- permissions ----
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
