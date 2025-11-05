from django.db import models
from django.utils import timezone

class Backup(models.Model):
    file = models.FileField(upload_to="backups/")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Backup"
        verbose_name_plural = "Backups"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Backup at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
