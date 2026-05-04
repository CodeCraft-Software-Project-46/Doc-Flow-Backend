from django.utils import timezone

def complete_task(task):
    task.completed_at = timezone.now()

    # SLA check
    if task.completed_at <= task.due_at:
        task.sla_status = "met"
    else:
        task.sla_status = "breached"

    task.status = "completed"
    task.save()

    return task