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
        parent_filter = request.GET.get('parent_filter', '')  # 'with_parent', 'without_parent', 'all'
        specific_parent = request.GET.get('specific_parent', '')  # Muayyan parent ID

        # Base queryset - barcha statement-lar
        statements = StatementStatistics.objects.all()

        # Parent filter qo'llash
        if parent_filter == 'without_parent':
            # Faqat parent yo'q statement-lar (parent=None)
            statements = statements.filter(parent__isnull=True)
        elif parent_filter == 'with_parent':
            # Faqat parent bor statement-lar
            statements = statements.filter(parent__isnull=False)
        elif specific_parent:
            # Muayyan parent-ning child-lari
            statements = statements.filter(parent_id=specific_parent)
        # 'all' yoki bo'sh bo'lsa - barchasi

        # Har bir statement uchun status bo'yicha count
        statistics = []

        for statement in statements:
            # Agar statement parent bo'lsa, barcha child-larini ham hisobga olish
            if statement.parent is None:
                # Parent statement - barcha child-larni qo'shish
                child_statements = self.get_all_children(statement)
                all_statement_ids = [statement.id] + [s.id for s in child_statements]
            else:
                # Child statement - faqat o'zini
                all_statement_ids = [statement.id]

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
                'statement_name_uz': getattr(statement, 'name_uz', statement.name),
                'parent_name_uz': getattr(statement.parent, 'name_uz', statement.parent.name) if statement.parent else '-',
                'is_parent': statement.parent is None,
                'saved': saved_count,
                'sent': sent_count,
                'cancelled': cancelled_count,
                'accepted': accepted_count,
                'total': total_count,
            })

        # Parent statement-larni dropdown uchun olish
        all_parent_statements = StatementStatistics.objects.filter(parent__isnull=True)

        extra_context = extra_context or {}
        extra_context['statistics'] = statistics
        extra_context['status_choices'] = Report.StatusChoices.choices
        extra_context['current_status'] = status_filter
        extra_context['parent_filter'] = parent_filter
        extra_context['specific_parent'] = specific_parent
        extra_context['all_parent_statements'] = all_parent_statements

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