from django.apps import AppConfig


class SlaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla"

    def ready(self):
        import sla.signals  # noqa: F401