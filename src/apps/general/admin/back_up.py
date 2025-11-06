from django.contrib import admin, messages
from django.urls import path, reverse
from django.http import HttpResponseRedirect, FileResponse, HttpResponse
import subprocess
import os
import zipfile
import datetime
from django.conf import settings
from apps.general.models.back_up import Backup
from apps.logs.mixins import AdminHistoryMixin

@admin.register(Backup)
class BackupAdmin(AdminHistoryMixin,admin.ModelAdmin):
    change_list_template = "admin/backup_changelist.html"
    list_display = ("file_link", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("file", "created_at")
    actions = ["export_as_zip"]  # <-- yangi action

    # ✅ qo‘shish tugmasini olib tashlaymiz
    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "run-backup/",
                self.admin_site.admin_view(self.run_backup),
                name="run-backup",
            ),
            path(
                "download/<int:backup_id>/",
                self.admin_site.admin_view(self.download_backup),
                name="download-backup",
            ),
        ]
        return custom_urls + urls

    def file_link(self, obj):
        if obj.file:
            url = reverse("admin:download-backup", args=[obj.id])
            return f'<a href="{url}" style="color:#2a7d2e;">⬇️ Download</a>'
        return "-"
    file_link.allow_tags = True
    file_link.short_description = "File"

    def run_backup(self, request):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_dir = os.path.join(settings.MEDIA_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_filename)

        script_path = "/app/docker/prod/backup.sh"
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        if result.returncode == 0:
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                dump_file = os.path.join(backup_dir, f"db_{timestamp}.sql")
                if os.path.exists(dump_file):
                    zipf.write(dump_file, os.path.basename(dump_file))

            relative_path = f"backups/{backup_filename}"
            Backup.objects.create(file=relative_path)
            messages.success(request, "✅ Backup successfully created!")
        else:
            messages.error(request, f"❌ Backup failed:\n{result.stderr}")

        changelist_url = reverse("admin:general_backup_changelist")
        return HttpResponseRedirect(changelist_url)

    def download_backup(self, request, backup_id):
        backup = Backup.objects.get(pk=backup_id)
        file_path = backup.file.path
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path))

    # ✅ Admin action — tanlangan backup fayllarni ZIP qilib eksport qilish
    def export_as_zip(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "❌ Hech qanday backup tanlanmadi!", level=messages.ERROR)
            return

        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"selected_backups_{timestamp}.zip"
        export_path = os.path.join(export_dir, export_name)

        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for backup in queryset:
                if backup.file and os.path.exists(backup.file.path):
                    zipf.write(backup.file.path, os.path.basename(backup.file.path))

        self.message_user(request, "✅ Tanlangan backuplar ZIP faylga eksport qilindi!")
        return FileResponse(open(export_path, "rb"), as_attachment=True, filename=export_name)

    export_as_zip.short_description = "📦 Export selected backups as ZIP"
