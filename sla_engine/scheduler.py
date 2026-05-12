from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from analytics.models import TaskInstance
from django.db.utils import OperationalError, DatabaseError

scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    try:
        if not scheduler.running:
            scheduler.start()
    except Exception as e:
        print("Scheduler start failed:", e)


def check_sla_status(task_id):
    print("🔥 SLA TRIGGER FIRED:", task_id)

    try:
        task = TaskInstance.objects.get(task_id=task_id)

        if not task.due_at:
            print("⚠️ SKIP: due_at is NULL")
            return

        now = timezone.now()

        if task.completed_at:
            status = "met" if task.completed_at <= task.due_at else "breached"
        else:
            status = "breached" if now >= task.due_at else None

        TaskInstance.objects.filter(task_id=task_id).update(
            sla_status=status
        )

        print(f"✅ SLA UPDATED -> {task.task_id} = {status}")

    except (OperationalError, DatabaseError) as e:
        print("🚨 DB ERROR (ignored safely):", e)

    except Exception as e:
        print("SLA Scheduler Error:", e)