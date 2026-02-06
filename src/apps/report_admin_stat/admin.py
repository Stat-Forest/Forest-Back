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
        specific_parent = request.GET.get('specific_parent', '')

        # FAQAT parent statement-larni olish (parent=None)
        if specific_parent:
            statements = StatementStatistics.objects.filter(id=specific_parent, parent__isnull=True)
        else:
            statements = StatementStatistics.objects.filter(parent__isnull=True)

        # Har bir parent statement uchun statistika
        statistics = []

        for statement in statements:
            # Parent statistikasi
            parent_stats = self.get_statement_stats(statement, status_filter)
            parent_stats['is_parent'] = True
            parent_stats['statement_id'] = statement.id
            statistics.append(parent_stats)

            # Child statement-lar statistikasi
            child_statements = StatementStatistics.objects.filter(parent=statement)
            for child in child_statements:
                child_stats = self.get_statement_stats(child, status_filter)
                child_stats['is_parent'] = False
                child_stats['parent_id'] = statement.id
                child_stats['statement_id'] = child.id
                statistics.append(child_stats)

        # Parent statement-larni dropdown uchun olish
        all_parent_statements = StatementStatistics.objects.filter(parent__isnull=True)

        # Umumiy statistikani hisoblash (faqat parent-lar uchun)
        parent_stats_only = [s for s in statistics if s.get('is_parent')]
        total_stats = {
            'total_reports': sum(s['total'] for s in parent_stats_only),
            'total_saved': sum(s['saved'] for s in parent_stats_only),
            'total_sent': sum(s['sent'] for s in parent_stats_only),
            'total_cancelled': sum(s['cancelled'] for s in parent_stats_only),
            'total_accepted': sum(s['accepted'] for s in parent_stats_only),
            'total_statements': len(parent_stats_only),
        }

        extra_context = extra_context or {}
        extra_context['statistics'] = statistics
        extra_context['status_choices'] = Report.StatusChoices.choices
        extra_context['current_status'] = status_filter
        extra_context['specific_parent'] = specific_parent
        extra_context['all_parent_statements'] = all_parent_statements
        extra_context['total_stats'] = total_stats

        return super().changelist_view(request, extra_context=extra_context)

    def get_statement_stats(self, statement, status_filter=''):
        """Bitta statement uchun statistika"""
        # Faqat shu statement uchun hisobotlar (child-larsiz)
        base_query = Report.objects.filter(
            statement_id=statement.id,
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

        # Child-lar sonini hisoblash
        child_count = StatementStatistics.objects.filter(parent=statement).count()

        return {
            'statement': statement,
            'statement_name_uz': getattr(statement, 'name_uz', statement.name),
            'child_count': child_count,
            'saved': saved_count,
            'sent': sent_count,
            'cancelled': cancelled_count,
            'accepted': accepted_count,
            'total': total_count,
        }

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
        specific_parent = request.GET.get('specific_parent', '')

        if specific_parent:
            statements = StatementStatistics.objects.filter(id=specific_parent, parent__isnull=True)
        else:
            statements = StatementStatistics.objects.filter(parent__isnull=True)

        statistics = []

        for statement in statements:
            # Parent statistikasi
            parent_stats = self.get_statement_stats(statement, status_filter)
            parent_stats['is_parent'] = True
            parent_stats['level'] = 0
            statistics.append(parent_stats)

            # Child statement-lar
            child_statements = StatementStatistics.objects.filter(parent=statement)
            for child in child_statements:
                child_stats = self.get_statement_stats(child, status_filter)
                child_stats['is_parent'] = False
                child_stats['level'] = 1
                statistics.append(child_stats)

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
            'Ички формалар сони',
            'Сақланган',
            'Юборилган',
            'Бекор қилинган',
            'Қабул қилинган',
            'Жами'
        ])

        # Data
        statistics = self.get_statistics_data(request)
        for stat in statistics:
            # Indent qo'shish (parent/child ko'rinishi uchun)
            indent = '  ' if not stat.get('is_parent') else ''
            name = f"{indent}{stat['statement_name_uz']}"

            # Child count faqat parent uchun
            child_info = str(stat['child_count']) if stat.get('is_parent') else '-'

            writer.writerow([
                name,
                child_info,
                stat['saved'],
                stat['sent'],
                stat['cancelled'],
                stat['accepted'],
                stat['total'],
            ])

        # Jami qator (faqat parent-lar uchun)
        parent_stats = [s for s in statistics if s.get('is_parent')]
        writer.writerow([])
        writer.writerow([
            'ЖАМИ:',
            '',
            sum(s['saved'] for s in parent_stats),
            sum(s['sent'] for s in parent_stats),
            sum(s['cancelled'] for s in parent_stats),
            sum(s['accepted'] for s in parent_stats),
            sum(s['total'] for s in parent_stats),
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

        # Styling
        header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        parent_fill = PatternFill(start_color="e6edff", end_color="e6edff", fill_type="solid")
        child_fill = PatternFill(start_color="f8f9fa", end_color="f8f9fa", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Headers
        headers = [
            'Ҳисобот формаси',
            'Ички формалар сони',
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

        row_idx = 2
        for stat in statistics:
            is_parent = stat.get('is_parent', False)

            # Indent uchun probel qo'shish
            indent = '' if is_parent else '    '
            name = f"{indent}{stat['statement_name_uz']}"

            # Fill color
            fill_color = parent_fill if is_parent else child_fill

            # Name
            cell = ws.cell(row=row_idx, column=1, value=name)
            cell.font = Font(bold=is_parent, size=11)
            cell.fill = fill_color
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center')

            # Child count (faqat parent uchun)
            child_info = stat['child_count'] if is_parent else '-'
            cell = ws.cell(row=row_idx, column=2, value=child_info)
            cell.fill = fill_color
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')

            # Statistics
            for col_idx, key in enumerate(['saved', 'sent', 'cancelled', 'accepted', 'total'], 3):
                cell = ws.cell(row=row_idx, column=col_idx, value=stat[key])
                cell.fill = fill_color
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.font = Font(bold=is_parent)

            row_idx += 1

        # Jami qator
        parent_stats = [s for s in statistics if s.get('is_parent')]
        total_row = row_idx + 1

        total_fill = PatternFill(start_color="d4d4ff", end_color="d4d4ff", fill_type="solid")

        cell = ws.cell(row=total_row, column=1, value='ЖАМИ:')
        cell.font = Font(bold=True, size=12)
        cell.fill = total_fill
        cell.border = border

        ws.cell(row=total_row, column=2, value='').fill = total_fill

        cell = ws.cell(row=total_row, column=3, value=sum(s['saved'] for s in parent_stats))
        cell.font = Font(bold=True)
        cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

        cell = ws.cell(row=total_row, column=4, value=sum(s['sent'] for s in parent_stats))
        cell.font = Font(bold=True)
        cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

        cell = ws.cell(row=total_row, column=5, value=sum(s['cancelled'] for s in parent_stats))
        cell.font = Font(bold=True)
        cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

        cell = ws.cell(row=total_row, column=6, value=sum(s['accepted'] for s in parent_stats))
        cell.font = Font(bold=True)
        cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

        cell = ws.cell(row=total_row, column=7, value=sum(s['total'] for s in parent_stats))
        cell.font = Font(bold=True)
        cell.fill = total_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')

        # Column widths
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
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