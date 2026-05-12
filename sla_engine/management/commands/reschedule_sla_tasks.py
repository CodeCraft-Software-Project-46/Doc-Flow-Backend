from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import TaskInstance
from sla_engine.scheduler import schedule_sla_job, check_sla_status, start_scheduler


class Command(BaseCommand):
    help = "Reschedule missed SLA tasks after server restart"

    def handle(self, *args, **options):
        start_scheduler()
        self.stdout.write("Rescheduling SLA tasks...\n")

        tasks = TaskInstance.objects.filter(sla_status__isnull=True, due_at__isnull=False)
        now = timezone.now()
        scheduled_count = 0

        for task in tasks:
            if task.due_at <= now:
                # Past due - evaluate immediately
                check_sla_status(task.task_id)
                task.refresh_from_db()
                self.stdout.write(
                    f"Task {task.task_id}: evaluated as {task.sla_status}"
                )
            else:
                # Future - reschedule
                schedule_sla_job(task.task_id, task.due_at)
                scheduled_count += 1
                self.stdout.write(
                    f"Task {task.task_id}: scheduled for {task.due_at}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Scheduled {scheduled_count} future task(s)."
            )
        )
