# apps/report_admin_stat/admin.py

from django.contrib import admin
from django.db.models import Count, Q
from apps.reports.models import Report
from .models import StatementStatistics


class StatementStatisticsAdmin(admin.ModelAdmin):
    """Parent statement-lar uchun hisobotlar statistikasi"""

    change_list_template = 'admin/reports/statement_statistics.html'

    def changelist_view(self, request, extra_context=None):
        # Filter parametrlari
        status_filter = request.GET.get('status', '')

        # Parent statement-larni olish (parent=None bo'lganlar)
        statements = StatementStatistics.objects.filter(parent__isnull=True)

        # Har bir statement uchun status bo'yicha count
        statistics = []

        for statement in statements:
            # Barcha child statement-larni olish (rekursiv)
            child_statements = self.get_all_children(statement)
            all_statement_ids = [statement.id] + [s.id for s in child_statements]

            # Base query
            base_query = Report.objects.filter(
                statement_id__in=all_statement_ids,
                is_report=True
            )

            # Status filter qo'llash
            if status_filter:
                base_query = base_query.filter(status=status_filter)

            # Har bir status uchun count
            saved_count = base_query.filter(status=Report.StatusChoices.SAVED).count()
            sent_count = base_query.filter(status=Report.StatusChoices.SENT).count()
            cancelled_count = base_query.filter(status=Report.StatusChoices.CANCELLED).count()
            accepted_count = base_query.filter(status=Report.StatusChoices.ACCEPTED).count()
            total_count = base_query.count()

            statistics.append({
                'statement': statement,
                'saved': saved_count,
                'sent': sent_count,
                'cancelled': cancelled_count,
                'accepted': accepted_count,
                'total': total_count,
            })

        extra_context = extra_context or {}
        extra_context['statistics'] = statistics
        extra_context['status_choices'] = Report.StatusChoices.choices
        extra_context['current_status'] = status_filter

        return super().changelist_view(request, extra_context=extra_context)

    def get_all_children(self, statement):
        """Rekursiv ravishda barcha child statement-larni olish"""
        children = []
        direct_children = StatementStatistics.objects.filter(parent=statement)

        for child in direct_children:
            children.append(child)
            children.extend(self.get_all_children(child))

        return children

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Proxy modelni registratsiya qilish
admin.site.register(StatementStatistics, StatementStatisticsAdmin)