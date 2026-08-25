from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from analytics.models import TaskInstance

from sla.services.sla_calculator import update_task_due_at
from sla.services.sla_service import (
    evaluate_sla,
)

# This file is the "when should we actually check this task" side of the
# SLA engine. sla_calculator.py works out the deadline, sla_service.py
# decides met/breached — this file makes sure that decision actually gets
# triggered, either right at the deadline (evaluate_sla_task) or as a
# catch-up safety net that runs every minute (reconcile_sla_tasks).


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def evaluate_sla_task(
    self,
    task_id,
):
    """
    Evaluate one task's SLA.

    This task is normally queued for the task's
    calculated due_at time.

    The periodic reconciliation task is the
    safety mechanism for missed/failed jobs.
    """

    # This is the actual "check one task" job. Celery is told to run it
    # exactly at the task's due_at time (see signals.py / reconcile below),
    # so most of the time this is what makes the met/breached decision.
    # If it fails partway through, autoretry_for above makes Celery try it
    # again automatically, up to 3 times.

    try:
        result = evaluate_sla(
            task_id
        )

        return {
            "task_id": task_id,
            "sla_status": result,
        }

    except TaskInstance.DoesNotExist:

        # The task was deleted before its due time arrived — nothing to do.
        return {
            "task_id": task_id,
            "sla_status": None,
            "message": "Task no longer exists.",
        }


# Cap per beat tick so a large backlog (bulk backfill, extended outage)
# drains gradually across ticks instead of loading millions of rows and
# firing that many Celery calls inside a single 60-second run.
RECONCILE_BATCH_SIZE = 2000


@shared_task
def reconcile_sla_tasks():
    """
    Periodic SLA reconciliation.

    Finds tasks whose SLA deadline has been reached
    and which have not yet received a final SLA decision.

    This allows the system to handle multiple tasks
    safely and provides a recovery mechanism if an
    individual scheduled task was missed.
    """

    # This job runs automatically every 60 seconds (see CELERY_BEAT_SCHEDULE
    # in settings.py) and does two separate jobs of its own:
    #
    #   1. Find tasks that exist but don't have a deadline yet, and give
    #      them one (see the first block below).
    #   2. Find tasks whose deadline has already passed but that somehow
    #      never got checked, and check them now (the second block below).
    #
    # Think of it as the safety net underneath the "check exactly at the
    # deadline" mechanism — if that ever gets missed for any reason, this
    # sweep catches it within a minute.

    now = timezone.now()

    # TaskInstance is populated by another part of the system.  When that
    # happens outside this Django process, post_save signals cannot run.  Pick
    # up those rows here, calculate their deadline once, and schedule their
    # exact-time Celery evaluation.
    #
    # In other words: this app doesn't create these task rows itself, so it
    # can't rely on "run this code the moment a task is created" — instead
    # it has to periodically look for tasks that showed up without a
    # deadline yet and calculate one for them here.
    uninitialized_task_ids = list(
        TaskInstance.objects.filter(
            due_at__isnull=True,
            created_at__isnull=False,
            sla_hours__isnull=False,
        )
        .order_by("task_id")
        .values_list("task_id", flat=True)[:RECONCILE_BATCH_SIZE]
    )

    scheduled_tasks = 0
    initialization_failures = []

    for task_id in uninitialized_task_ids:
        try:
            # Work out and save this task's deadline...
            due_at = update_task_due_at(task_id)
            # ...then tell Celery "check this task's SLA at exactly that
            # moment" (eta=due_at schedules it for the future, not now).
            evaluate_sla_task.apply_async(args=[task_id], eta=due_at)
            scheduled_tasks += 1
        except TaskInstance.DoesNotExist:
            # The source system deleted the task between discovery and setup.
            continue
        except Exception as error:
            initialization_failures.append(
                {"task_id": task_id, "error": str(error)}
            )

    overdue_task_ids = list(
        TaskInstance.objects.filter(
            due_at__isnull=False,
            due_at__lte=now,
        )
        .exclude(task_id__in=uninitialized_task_ids)
        .exclude(
            sla_status__in=[
                "met",
                "breached",
            ]
        )
        .order_by("due_at")
        .values_list(
            "task_id",
            flat=True,
        )[:RECONCILE_BATCH_SIZE]
    )

    queued_tasks = 0

    for task_id in overdue_task_ids:

        # These are already overdue, so check them right away instead of
        # scheduling them for a future time.
        evaluate_sla_task.delay(
            task_id
        )

        queued_tasks += 1

    return {
        "scheduled_tasks": scheduled_tasks,
        "queued_tasks": queued_tasks,
        "initialization_failures": initialization_failures,
        "checked_at": now.isoformat(),
    }
