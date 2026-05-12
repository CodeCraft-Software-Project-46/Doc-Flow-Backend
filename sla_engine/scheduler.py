from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from analytics.models import TaskInstance
from django.db.utils import OperationalError, DatabaseError
from django.db import close_old_connections

scheduler = BackgroundScheduler(daemon=True)


def resolve_sla_status(task, now=None):
    if now is None:
        now = timezone.now()

    if task.completed_at:
        return "met" if task.completed_at <= task.due_at else "breached"

    if now >= task.due_at:
        return "breached"

    return None


def schedule_sla_job(task_id, run_date):
    job_id = f"sla_task_{task_id}"

    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)

    scheduler.add_job(
        check_sla_status,
        trigger="date",
        run_date=run_date,
        args=[task_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )


def start_scheduler():
    try:
        if not scheduler.running:
            scheduler.start()
    except Exception as e:
        print("Scheduler start failed:", e)


def check_sla_status(task_id):
    print("SLA TRIGGER FIRED:", task_id)

    try:
        close_old_connections()
        task = TaskInstance.objects.get(task_id=task_id)

        if not task.due_at:
            print("⚠️ SKIP: due_at is NULL")
            return

        now = timezone.now()
        status = resolve_sla_status(task, now)

        if status is None:
            # The scheduler can wake a fraction early; re-queue the job at the
            # exact due time instead of persisting NULL.
            schedule_sla_job(task.task_id, task.due_at)
            print(f"SLA REQUEUED -> {task.task_id} for {task.due_at}")
            return

        TaskInstance.objects.filter(task_id=task_id).update(sla_status=status)

        print(f"SLA UPDATED -> {task.task_id} = {status}")

    except (OperationalError, DatabaseError) as e:
        print("DB ERROR (ignored safely):", e)

    except Exception as e:
        print("SLA Scheduler Error:", e)