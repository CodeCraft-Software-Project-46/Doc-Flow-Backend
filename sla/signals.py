from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from analytics.models import TaskInstance

from sla.services.sla_calculator import (
    update_task_due_at,
)

from sla.tasks import (
    evaluate_sla_task,
)

# A Django "signal" is just a way of saying "whenever X happens anywhere in
# the app, automatically run this function." Here, X is "a new TaskInstance
# row gets saved" — so whenever that happens (through this Django app; see
# the note in reconcile_sla_tasks about tasks created elsewhere), this file
# immediately works out that task's deadline and schedules its SLA check.
# This is the "instant" path — reconcile_sla_tasks() is the backup path for
# whenever this one doesn't fire.


@receiver(
    post_save,
    sender=TaskInstance,
)
def initialize_task_sla(
    sender,
    instance,
    created,
    raw,
    **kwargs,
):
    """
    When a new TaskInstance is created:

    1. Calculate due_at.
    2. Save due_at.
    3. Queue a Celery evaluation task.

    Celery Beat also performs periodic reconciliation
    as a safety mechanism.
    """

    # `raw` is True during things like loading a fixture file — skip those,
    # we only care about real task creation.
    if raw:
        return

    # We only care about brand-new tasks, not every time an existing task
    # gets updated (e.g. when it later gets marked completed).
    if not created:
        return

    # Can't calculate a deadline without knowing when the task started or
    # how many hours its SLA gives it — bail out quietly if either is
    # missing (reconcile_sla_tasks will pick it up later once they're set).
    if instance.created_at is None:
        return

    if instance.sla_hours is None:
        return

    try:
        # Work out this task's deadline right now and save it.
        due_at = update_task_due_at(
            instance.task_id
        )

        # A worker may receive an ETA job before the outer database
        # transaction commits. Schedule only after the task row is visible.
        #
        # In plain terms: we wait until Django has actually finished saving
        # the task to the database before telling Celery to check it later —
        # otherwise Celery might try to look up a task that, from its point
        # of view, doesn't exist yet.
        transaction.on_commit(
            lambda task_id=instance.task_id, eta=due_at: (
                evaluate_sla_task.apply_async(
                    args=[task_id],
                    eta=eta,
                )
            )
        )

    except Exception:
        # Do not silently hide SLA configuration
        # errors in production.
        raise
