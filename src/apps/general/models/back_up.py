from django.db import models

class Backup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Backup"
        verbose_name_plural = "Backups"

    def __str__(self):
        return f"Backup at {self.created_at}"
