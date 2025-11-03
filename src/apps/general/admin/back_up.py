from django.contrib import admin, messages
from django.urls import path
from django.http import HttpResponse
from django.utils import timezone
import subprocess
import os

from apps.general.models.back_up import Backup

class BackupAdmin(admin.ModelAdmin):
    change_list_template = "admin/backup_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("run-backup/", self.admin_site.admin_view(self.run_backup), name="run-backup"),
        ]
        return custom_urls + urls

    def run_backup(self, request):
        # Backup script path
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker/prod/backup.sh"))

        # Run the shell script
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        if result.returncode == 0:
            messages.success(request, "✅ Backup successfully created!")
        else:
            messages.error(request, f"❌ Backup failed:\n{result.stderr}")

        return HttpResponse('<script>window.location.href="/admin/backup/";</script>')

admin.site.register(Backup, BackupAdmin)
