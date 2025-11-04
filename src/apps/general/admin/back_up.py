from django.contrib import admin, messages
from django.urls import path, reverse
from django.http import HttpResponseRedirect
import subprocess
import os
from apps.general.models.back_up import Backup


class BackupAdmin(admin.ModelAdmin):
    change_list_template = "admin/backup_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "run-backup/",
                self.admin_site.admin_view(self.run_backup),
                name="run-backup",
            ),
        ]
        return custom_urls + urls

    def run_backup(self, request):
        # To‘g‘ri joylashgan backup.sh yo‘li
        script_path = "/app/docker/prod/backup.sh"

        # Run the shell script
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        if result.returncode == 0:
            messages.success(request, "✅ Backup successfully created!")
        else:
            messages.error(request, f"❌ Backup failed:\n{result.stderr}")

        # Admin sahifasiga qaytish
        changelist_url = reverse("admin:general_backup_changelist")
        return HttpResponseRedirect(changelist_url)


admin.site.register(Backup, BackupAdmin)
