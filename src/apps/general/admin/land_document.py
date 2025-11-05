from django.contrib import admin, messages
from django.http import HttpResponse
import csv
import io
from docx import Document
from reportlab.pdfgen import canvas
from datetime import datetime

from apps.general.models.land_document import LandDocument


@admin.register(LandDocument)
class LandDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "date", "created_at")
    search_fields = ("name", "organization__name")
    list_filter = ("organization", "date")
    date_hierarchy = "date"
    actions = ["export_files_as_excel", "export_files_as_word", "export_files_as_pdf"]

    # ✅ Custom date filter (YYYY/MM/DD)
    def get_search_results(self, request, queryset, search_term):
        """
        Allows searching by YYYY/MM/DD formatted date
        """
        try:
            if "/" in search_term:
                # convert "2025/11/05" → date object
                date_obj = datetime.strptime(search_term, "%Y/%m/%d").date()
                queryset |= self.model.objects.filter(date=date_obj)
        except ValueError:
            pass
        return super().get_search_results(request, queryset, search_term)

    # ✅ Helper function: only docs with files
    def _get_queryset_with_files(self, queryset):
        """Return only documents that have uploaded files."""
        return queryset.exclude(file="").exclude(file__isnull=True)

    # ✅ Export to Excel (CSV) — only file paths
    def export_files_as_excel(self, request, queryset):
        queryset = self._get_queryset_with_files(queryset)
        if not queryset.exists():
            self.message_user(request, "No uploaded files found for export!", level=messages.WARNING)
            return

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="land_document_files.csv"'
        writer = csv.writer(response)
        writer.writerow(["File URL"])

        for obj in queryset:
            writer.writerow([obj.file.url if obj.file else ""])
        return response

    export_files_as_excel.short_description = "📊 Export only files (CSV)"

    # ✅ Export to Word
    def export_files_as_word(self, request, queryset):
        queryset = self._get_queryset_with_files(queryset)
        if not queryset.exists():
            self.message_user(request, "No uploaded files found for export!", level=messages.WARNING)
            return

        document = Document()
        document.add_heading('LandDocument Files Export', 0)

        for obj in queryset:
            if obj.file:
                document.add_paragraph(obj.file.url)

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = 'attachment; filename="land_document_files.docx"'
        return response

    export_files_as_word.short_description = "📝 Export only files (Word)"

    # ✅ Export to PDF
    def export_files_as_pdf(self, request, queryset):
        queryset = self._get_queryset_with_files(queryset)
        if not queryset.exists():
            self.message_user(request, "No uploaded files found for export!", level=messages.WARNING)
            return

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="land_document_files.pdf"'
        pdf = canvas.Canvas(response)

        y = 800
        pdf.setFont("Helvetica", 12)
        pdf.drawString(200, y + 20, "LandDocument Files Export")
        y -= 40

        for obj in queryset:
            if obj.file:
                pdf.drawString(50, y, obj.file.url)
                y -= 20
                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 12)
                    y = 800

        pdf.save()
        return response

    export_files_as_pdf.short_description = "📄 Export only files (PDF)"
