from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "apps.logs"

    def ready(self):
        from apps.logs.signals import connect_history_signals
        connect_history_signals()