from django.contrib import admin, messages
from django.http import FileResponse
from django.conf import settings
import os
import tempfile
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

        # ZIP vaqtinchalik faylda (MEDIA_ROOT/exports emas — nginx /media/ ni login'siz
        # tarqatadi); FileResponse yopganda fayl o'chadi.
        tmp = tempfile.TemporaryFile(suffix=".zip")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"land_documents_{timestamp}.zip"

        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zipf:
            for obj in queryset:
                if obj.file and os.path.exists(obj.file.path):
                    # faylni original nomi bilan ZIP ichiga qo‘shamiz
                    filename = os.path.basename(obj.file.name)
                    zipf.write(obj.file.path, filename)

        self.message_user(request, f"✅ {queryset.count()} ta fayl ZIP formatda eksport qilindi!")

        tmp.seek(0)
        return FileResponse(tmp, as_attachment=True, filename=export_name)

    export_files_as_zip.short_description = "📦 Tanlangan hujjat fayllarini ZIP formatda eksport qilish"
