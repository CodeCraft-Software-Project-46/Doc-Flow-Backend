from django.db import transaction
from django.utils import timezone

from analytics.models import TaskInstance

# This file answers the second half of the SLA question: once we know a
# task's deadline (due_at, worked out by sla_calculator.py), did the task
# actually meet it or breach it?


COMPLETED_STATUS_VALUES = {
    "completed",
    "complete",
    "done",
    "approved",
    "closed",
    "finished",
}


def is_task_completed(task):
    """
    Determine whether a task is completed.

    completed_at is the preferred source because
    SLA accuracy depends on the actual completion timestamp.
    """

    # This only answers "is it done?" — it does NOT tell us whether it was
    # done on time. That's a separate question, answered in
    # resolve_sla_status() below by comparing actual timestamps.

    # completed_at being set is the strongest signal: it's an actual
    # timestamp, not just a status label, so trust it first.
    if task.completed_at is not None:
        return True

    status = getattr(
        task,
        "status",
        None,
    )

    if status is None:
        return False

    # Fall back to checking if the status text looks like "done" in some
    # form, in case completed_at wasn't set for some reason.
    return (
        str(status)
        .strip()
        .lower()
        in COMPLETED_STATUS_VALUES
    )


def resolve_sla_status(
    task,
    now=None,
):
    """
    Determine the SLA decision.

    Rules:

    1. Completed at or before due_at -> met
    2. Completed after due_at -> breached
    3. Not completed at due_at -> breached
    4. Not yet due -> no decision
    """

    if now is None:
        now = timezone.now()

    # If we don't even know when this task is due yet, we can't judge it —
    # come back once due_at has been calculated.
    if task.due_at is None:
        return None

    # --- Task IS completed: compare the two timestamps to see if it was on time. ---
    if task.completed_at is not None:

        if task.completed_at <= task.due_at:
            return "met"

        return "breached"

    # --- Task's completed_at is missing. Is it "done" some other way (status text)? ---
    # If so, we know it finished, but we have no timestamp to compare
    # against due_at — so we genuinely can't say "met" or "breached" yet.
    # Returning None here means "no decision yet", not "it failed".
    if is_task_completed(task):
        return None

    # --- Task is still genuinely running. Has the deadline already passed? ---
    if now >= task.due_at:
        return "breached"

    # Still running, and the deadline hasn't arrived yet — nothing to decide.
    return None


@transaction.atomic
def evaluate_sla(
    task_id,
    evaluation_time=None,
):
    """
    Evaluate and persist one task's SLA status.
    """

    # Lock this task's row while we check and possibly update it, so two
    # evaluations can't run for the same task at the exact same instant.
    task = (
        TaskInstance.objects
        .select_for_update()
        .get(task_id=task_id)
    )

    if task.due_at is None:
        return None

    # Never overwrite a final decision.
    #
    # Once a task has been marked "met" or "breached", that's permanent —
    # this function will never flip it back or re-decide it, even if it
    # gets called again later (e.g. by the periodic safety-net job).
    if task.sla_status in {
        "met",
        "breached",
    }:
        return task.sla_status

    if evaluation_time is None:
        evaluation_time = timezone.now()

    status = resolve_sla_status(
        task,
        now=evaluation_time,
    )

    # resolve_sla_status() returning None means "not ready to decide yet" —
    # in that case, leave the task alone and don't save anything.
    if status is None:
        return None

    task.sla_status = status
    task.sla_evaluated_at = evaluation_time

    task.save(
        update_fields=[
            "sla_status",
            "sla_evaluated_at",
        ]
    )

    return status
