import os
import sys
from django.apps import AppConfig


class SlaEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla_engine"

    def ready(self):
        # Import signals so TaskInstance post_save handler is always registered.
        from sla_engine import signals  # noqa: F401

        # Skip startup for commands where background scheduler is not needed.
        skip_commands = {"makemigrations", "migrate", "collectstatic", "test"}
        argv = set(sys.argv)
        if skip_commands.intersection(argv):
            return

        # For runserver, start only in the reloader main child.
        is_runserver = "runserver" in argv
        if is_runserver and os.environ.get("RUN_MAIN") != "true":
            return

        try:
            from sla_engine.scheduler import start_scheduler

            start_scheduler()
            print("APScheduler started for SLA jobs")
        except Exception as e:
            print(f"Scheduler startup error: {e}")