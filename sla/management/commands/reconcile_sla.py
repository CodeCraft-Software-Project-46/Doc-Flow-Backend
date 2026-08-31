from django.core.management.base import BaseCommand

from sla.tasks import reconcile_sla_tasks


class Command(BaseCommand):
    help = (
        "Reconcile SLA tasks whose due time has been reached."
    )

    def handle(self, *args, **options):

        result = reconcile_sla_tasks()

        self.stdout.write(
            self.style.SUCCESS(
                "SLA reconciliation completed. "
                f"Scheduled {result.get('scheduled_tasks', 0)} "
                "new task(s), "
                f"Queued {result.get('queued_tasks', 0)} "
                "overdue task(s)."
            )
        )

        for failure in result.get("initialization_failures", []):
            self.stderr.write(
                self.style.ERROR(
                    "Could not initialize SLA for "
                    f"task {failure['task_id']}: {failure['error']}"
                )
            )
