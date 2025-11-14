from django.contrib import admin, messages
from django.http import FileResponse
from django.conf import settings
import os
import zipfile
import datetime

from apps.general.models.land_document import LandDocument
from apps.logs.mixins import AdminHistoryMixin


@admin.register(LandDocument)
class LandDocumentAdmin(AdminHistoryMixin, admin.ModelAdmin):
    list_display = ("name", "organization", "date", "created_at")
    search_fields = ("name", "organization__name")
    list_filter = ("organization", "date")
    date_hierarchy = "date"
    actions = ["export_files_as_zip"]

    # ✅ Faqat fayli mavjud bo‘lgan obyektlarni olish
    def _get_queryset_with_files(self, queryset):
        return queryset.exclude(file="").exclude(file__isnull=True)

    # ✅ ZIP formatda hujjatlarni eksport qilish
    def export_files_as_zip(self, request, queryset):
        queryset = self._get_queryset_with_files(queryset)

        if not queryset.exists():
            self.message_user(request, "❌ Fayli mavjud hujjatlar topilmadi!", level=messages.WARNING)
            return

        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"land_documents_{timestamp}.zip"
        export_path = os.path.join(export_dir, export_name)

        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for obj in queryset:
                if obj.file and os.path.exists(obj.file.path):
                    # faylni original nomi bilan ZIP ichiga qo‘shamiz
                    filename = os.path.basename(obj.file.name)
                    zipf.write(obj.file.path, filename)

        self.message_user(request, f"✅ {queryset.count()} ta fayl ZIP formatda eksport qilindi!")

        return FileResponse(open(export_path, "rb"), as_attachment=True, filename=export_name)

    export_files_as_zip.short_description = "📦 Tanlangan hujjat fayllarini ZIP formatda eksport qilish"
