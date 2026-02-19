from django.db import models
from django.utils import timezone
#
def backup_upload_path(instance, filename):
    date = timezone.now()
    return f"backups/{date.year}/{date.month:02d}/{date.day:02d}/{filename}"

class Backup(models.Model):
    file = models.FileField(upload_to=backup_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Backup"
        verbose_name_plural = "Backups"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Backup at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
