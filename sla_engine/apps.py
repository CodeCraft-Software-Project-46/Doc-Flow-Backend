from django.apps import AppConfig


class SlaEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla_engine"

    def ready(self):
        import sla_engine.signals
        from sla_engine.scheduler import start_scheduler

        start_scheduler()