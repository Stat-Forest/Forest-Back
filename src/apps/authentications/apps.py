from django.apps import AppConfig


class AuthenticationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentications"

    def ready(self):
        """
        Import OpenAPI extension to register CustomJWTAuthentication with drf-spectacular.
        This must be called at Django startup so the extension is registered before
        schema generation occurs.
        """
        import apps.authentications.openapi
