from django.utils import timezone
from sla_engine.services.sla_calculator import calculate_due_at
from sla_engine.utils.working_time import next_working_day_start
def create_task_with_sla(task, sla_config, workflow_config):
    """
    Call this when task is created
    """

    created_at = task.created_at or timezone.now()

    due_at = calculate_due_at(
        created_at,
        task.sla_hours,
        workflow_config
    )

    task.due_at = due_at
    task.sla_status = "pending"
    task.save()

    return task