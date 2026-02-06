# apps/report_admin_stat/admin.py

from django.contrib import admin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
import csv
from apps.reports.models import Report
from .models import StatementStatistics


class StatementStatisticsAdmin(admin.ModelAdmin):
    """Parent statement-lar uchun hisobotlar statistikasi"""

    change_list_template = 'admin/reports/statement_statistics.html'

    def changelist_view(self, request, extra_context=None):
        # Export funksiyasi
        if request.GET.get('export') == 'csv':
            return self.export_to_csv(request)

        if request.GET.get('export') == 'excel':
            return self.export_to_excel(request)

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
                'parent_name_uz': getattr(statement.parent, 'name_uz',
                                          statement.parent.name) if statement.parent else '-',
                'is_parent': statement.parent is None,
                'saved': saved_count,
                'sent': sent_count,
                'cancelled': cancelled_count,
                'accepted': accepted_count,
                'total': total_count,
            })

        # Parent statement-larni dropdown uchun olish
        all_parent_statements = StatementStatistics.objects.filter(parent__isnull=True)

        # Umumiy statistikani hisoblash
        total_stats = {
            'total_reports': sum(s['total'] for s in statistics),
            'total_saved': sum(s['saved'] for s in statistics),
            'total_sent': sum(s['sent'] for s in statistics),
            'total_cancelled': sum(s['cancelled'] for s in statistics),
            'total_accepted': sum(s['accepted'] for s in statistics),
            'total_statements': len(statistics),
        }

        extra_context = extra_context or {}
        extra_context['statistics'] = statistics
        extra_context['status_choices'] = Report.StatusChoices.choices
        extra_context['current_status'] = status_filter
        extra_context['parent_filter'] = parent_filter
        extra_context['specific_parent'] = specific_parent
        extra_context['all_parent_statements'] = all_parent_statements
        extra_context['total_stats'] = total_stats

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

    def get_statistics_data(self, request):
        """Statistika ma'lumotlarini olish (export uchun)"""
        status_filter = request.GET.get('status', '')
        parent_filter = request.GET.get('parent_filter', '')
        specific_parent = request.GET.get('specific_parent', '')

        statements = StatementStatistics.objects.all()

        if parent_filter == 'without_parent':
            statements = statements.filter(parent__isnull=True)
        elif parent_filter == 'with_parent':
            statements = statements.filter(parent__isnull=False)
        elif specific_parent:
            statements = statements.filter(parent_id=specific_parent)

        statistics = []

        for statement in statements:
            if statement.parent is None:
                child_statements = self.get_all_children(statement)
                all_statement_ids = [statement.id] + [s.id for s in child_statements]
            else:
                all_statement_ids = [statement.id]

            base_query = Report.objects.filter(
                statement_id__in=all_statement_ids,
                is_report=True
            )

            if status_filter:
                base_query = base_query.filter(status=status_filter)

            saved_count = base_query.filter(status=Report.StatusChoices.SAVED).count()
            sent_count = base_query.filter(status=Report.StatusChoices.SENT).count()
            cancelled_count = base_query.filter(status=Report.StatusChoices.CANCELLED).count()
            accepted_count = base_query.filter(status=Report.StatusChoices.ACCEPTED).count()
            total_count = base_query.count()

            statistics.append({
                'statement': statement,
                'statement_name_uz': getattr(statement, 'name_uz', statement.name),
                'parent_name_uz': getattr(statement.parent, 'name_uz',
                                          statement.parent.name) if statement.parent else '-',
                'is_parent': statement.parent is None,
                'saved': saved_count,
                'sent': sent_count,
                'cancelled': cancelled_count,
                'accepted': accepted_count,
                'total': total_count,
            })

        return statistics

    def export_to_csv(self, request):
        """CSV formatda export qilish"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="statement_statistics_{timestamp}.csv"'

        # UTF-8 BOM qo'shish (Excel uchun)
        response.write('\ufeff')

        writer = csv.writer(response)

        # Header
        writer.writerow([
            'Ҳисобот формаси',
            'Юқори форма',
            'Сақланган',
            'Юборилган',
            'Бекор қилинган',
            'Қабул қилинган',
            'Жами'
        ])

        # Data
        statistics = self.get_statistics_data(request)
        for stat in statistics:
            writer.writerow([
                stat['statement_name_uz'],
                stat['parent_name_uz'],
                stat['saved'],
                stat['sent'],
                stat['cancelled'],
                stat['accepted'],
                stat['total'],
            ])

        # Jami qator
        writer.writerow([])
        writer.writerow([
            'ЖАМИ:',
            '',
            sum(s['saved'] for s in statistics),
            sum(s['sent'] for s in statistics),
            sum(s['cancelled'] for s in statistics),
            sum(s['accepted'] for s in statistics),
            sum(s['total'] for s in statistics),
        ])

        return response

    def export_to_excel(self, request):
        """Excel formatda export qilish"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            return HttpResponse("openpyxl kutubxonasi o'rnatilmagan. pip install openpyxl", status=500)

        wb = Workbook()
        ws = wb.active
        ws.title = "Statistika"

        # Header styling
        header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Headers
        headers = [
            'Ҳисобот формаси',
            'Юқори форма',
            'Сақланган',
            'Юборилган',
            'Бекор қилинган',
            'Қабул қилинган',
            'Жами'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # Data
        statistics = self.get_statistics_data(request)

        for row_idx, stat in enumerate(statistics, 2):
            ws.cell(row=row_idx, column=1, value=stat['statement_name_uz'])
            ws.cell(row=row_idx, column=2, value=stat['parent_name_uz'])
            ws.cell(row=row_idx, column=3, value=stat['saved'])
            ws.cell(row=row_idx, column=4, value=stat['sent'])
            ws.cell(row=row_idx, column=5, value=stat['cancelled'])
            ws.cell(row=row_idx, column=6, value=stat['accepted'])
            ws.cell(row=row_idx, column=7, value=stat['total'])

            # Styling
            for col in range(1, 8):
                cell = ws.cell(row=row_idx, column=col)
                cell.border = border
                cell.alignment = Alignment(horizontal='left' if col <= 2 else 'center', vertical='center')

                # Parent row styling
                if stat['is_parent']:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="f0f4ff", end_color="f0f4ff", fill_type="solid")

        # Jami qator
        total_row = len(statistics) + 3
        ws.cell(row=total_row, column=1, value='ЖАМИ:').font = Font(bold=True, size=12)
        ws.cell(row=total_row, column=3, value=sum(s['saved'] for s in statistics)).font = Font(bold=True)
        ws.cell(row=total_row, column=4, value=sum(s['sent'] for s in statistics)).font = Font(bold=True)
        ws.cell(row=total_row, column=5, value=sum(s['cancelled'] for s in statistics)).font = Font(bold=True)
        ws.cell(row=total_row, column=6, value=sum(s['accepted'] for s in statistics)).font = Font(bold=True)
        ws.cell(row=total_row, column=7, value=sum(s['total'] for s in statistics)).font = Font(bold=True)

        # Column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 12

        # Response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="statement_statistics_{timestamp}.xlsx"'

        wb.save(response)
        return response


# Proxy modelni registratsiya qilish
admin.site.register(StatementStatistics, StatementStatisticsAdmin)