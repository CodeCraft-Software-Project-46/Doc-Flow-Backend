from analytics.models import TaskInstance
from django.utils import timezone

def evaluate_sla(task_id):

    task = TaskInstance.objects.get(task_id=task_id)
    now = timezone.now()

    if task.completed_at:
        status = "met" if task.completed_at <= task.due_at else "breached"
    else:
        status = "breached" if now >= task.due_at else None

    task = TaskInstance.objects.get(task_id=task_id)
    task.sla_status = status
    task.save(update_fields=["sla_status"])