import os
from django.apps import AppConfig


class SlaEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla_engine"

    def ready(self):

        # ❗ NEVER run during tests
        if os.environ.get("RUN_MAIN") != "true":
            return

        try:
            from sla_engine.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print("Scheduler start skipped:", e)