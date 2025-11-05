from django.contrib import admin, messages
from django.urls import path, reverse
from django.http import HttpResponseRedirect, FileResponse
import subprocess
import os
import zipfile
import datetime
from django.conf import settings
from apps.general.models.back_up import Backup


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    change_list_template = "admin/backup_changelist.html"
    list_display = ("file_link", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("file", "created_at")

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
        # Backup fayl nomini yaratamiz
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_dir = os.path.join(settings.MEDIA_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_filename)

        # backup.sh scriptni ishga tushiramiz
        script_path = "/app/docker/prod/backup.sh"
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        if result.returncode == 0:
            # zip faylni yaratamiz (odatda script db dump qiladi, biz uni ziplaymiz)
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                dump_file = os.path.join(backup_dir, f"db_{timestamp}.sql")
                if os.path.exists(dump_file):
                    zipf.write(dump_file, os.path.basename(dump_file))

            # bazaga yozamiz
            relative_path = f"backups/{backup_filename}"
            Backup.objects.create(file=relative_path)
            messages.success(request, "✅ Backup successfully created and saved as ZIP!")
        else:
            messages.error(request, f"❌ Backup failed:\n{result.stderr}")

        changelist_url = reverse("admin:general_backup_changelist")
        return HttpResponseRedirect(changelist_url)

    def download_backup(self, request, backup_id):
        backup = Backup.objects.get(pk=backup_id)
        file_path = backup.file.path
        return FileResponse(open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path))
