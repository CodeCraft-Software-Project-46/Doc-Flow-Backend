from apscheduler.schedulers.background import BackgroundScheduler
from analytics.models import TaskInstance
from django.utils import timezone

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def check_sla_status(task_id):
    print("🔥 SLA TRIGGER FIRED:", task_id)

    try:
        task = TaskInstance.objects.get(task_id=task_id)

        now = timezone.now()

        if task.completed_at:
            status = "met" if task.completed_at <= task.due_at else "breached"
        else:
            status = "breached" if now >= task.due_at else "breached"

        TaskInstance.objects.filter(task_id=task_id).update(
            sla_status=status
        )

        print(f"✅ SLA UPDATED -> {task.task_id} = {status}")

    except Exception as e:
        print("SLA Scheduler Error:", e)