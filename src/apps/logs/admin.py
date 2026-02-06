from django.urls import path
from django.contrib import admin
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter
from django.db.models import Case, When, Value, IntegerField
from openpyxl import Workbook

from .models import HistoryActionJournal


# =======================
# USER LOGIN FILTER
# =======================
class UserLoginFilter(SimpleListFilter):
    title = "User login status"
    parameter_name = "user_login_status"

    def lookups(self, request, model_admin):
        return (
            ('login_users', 'Login qilgan userlar'),
            ('never_login_users', 'Login qilmagan userlar'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'login_users':
            return queryset.filter(user__last_login__isnull=False)
        if self.value() == 'never_login_users':
            return queryset.filter(user__last_login__isnull=True)
        return queryset


# =======================
# ORGANIZATION LOGIN FILTER
# =======================
class OrganizationLoginFilter(SimpleListFilter):
    title = "Organization login status"
    parameter_name = "organization_login_status"

    def lookups(self, request, model_admin):
        return (
            ('login_orgs', 'Login qilgan organizationlar'),
            ('never_login_orgs', 'Login qilmagan organizationlar'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'login_orgs':
            return queryset.filter(
                user__organization__user__last_login__isnull=False
            ).distinct()

        if self.value() == 'never_login_orgs':
            return queryset.exclude(
                user__organization__user__last_login__isnull=False
            ).distinct()

        return queryset


# =======================
# ORGANIZATION ORDER FILTER
# =======================
class OrganizationLoginOrderFilter(SimpleListFilter):
    title = "Order by organization activity"
    parameter_name = "organization_order"

    def lookups(self, request, model_admin):
        return (
            ('active_first', 'Active organizationlar (login bor)'),
            ('inactive_first', 'Inactive organizationlar (login yo‘q)'),
        )

    def queryset(self, request, queryset):
        if self.value() in ('active_first', 'inactive_first'):
            qs = queryset.annotate(
                org_active=Case(
                    When(
                        user__organization__user__last_login__isnull=False,
                        then=Value(1)
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
            if self.value() == 'active_first':
                return qs.order_by('-org_active', '-created_at')
            return qs.order_by('org_active', '-created_at')

        return queryset


# =======================
# ADMIN CONFIG
# =======================
@admin.register(HistoryActionJournal)
class HistoryActionJournalAdmin(admin.ModelAdmin):

    # -------- LIST VIEW ----------
    list_display = (
        'user',
        'user_organization',
        'action',
        'model_name',
        'object_repr',
        'change_message',
        'created_at',
    )

    # -------- FILTERS ----------
    list_filter = (
        UserLoginFilter,
        OrganizationLoginFilter,
        OrganizationLoginOrderFilter,
        'user__organization',
        'model_name',
        'action',
        'created_at',
    )

    # -------- SEARCH ----------
    search_fields = (
        'user__email',
        'model_name',
        'object_repr',
        'change_message',
    )

    actions = ['export_as_excel']

    # -------- CUSTOM DISPLAY ----------
    def user_organization(self, obj):
        if obj.user and getattr(obj.user, 'organization', None):
            return obj.user.organization.name_uz
        return "-"
    user_organization.short_description = "Organization"

    # -------- EXCEL GENERATOR ----------
    def _create_excel_response(self, rows, filename="history_export.xlsx"):
        wb = Workbook()
        ws = wb.active
        ws.title = "History Export"

        ws.append([
            "User",
            "Organization",
            "Action",
            "Model Name",
            "Object Repr",
            "Change Message",
            "Created At",
        ])

        for obj in rows:
            ws.append([
                obj.user.email if obj.user else "-",
                obj.user.organization.name_uz if (
                    obj.user and getattr(obj.user, 'organization', None)
                ) else "-",
                obj.action,
                obj.model_name,
                obj.object_repr,
                obj.change_message,
                obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    # -------- ACTION: EXPORT SELECTED ----------
    def export_as_excel(self, request, queryset):
        return self._create_excel_response(queryset)

    export_as_excel.short_description = "Export selected to Excel"

    # -------- CUSTOM URL: EXPORT ALL ----------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-all/',
                self.admin_site.admin_view(self.export_all_logs),
                name='history_export_all',
            ),
        ]
        return custom_urls + urls

    def export_all_logs(self, request):
        rows = HistoryActionJournal.objects.all()
        return self._create_excel_response(rows, filename="all_history_logs.xlsx")

    # -------- ADMIN PAGE CONTEXT ----------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_all_url'] = 'export-all/'
        return super().changelist_view(request, extra_context=extra_context)

    # -------- PERMISSIONS ----------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
