from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.utils import timezone

from analytics.models import TaskInstance
from working_hours.models import WorkingHoursConfig
from sla_engine.scheduler import scheduler, check_sla_status


def ensure_time(value):
    if isinstance(value, str):
        return datetime.strptime(value.split(".")[0], "%H:%M:%S").time()
    return value


def is_working_day(date_obj, config):
    python_weekday = date_obj.weekday()
    converted_weekday = (python_weekday + 1) % 7

    if converted_weekday not in config.work_days:
        return False

    if date_obj.strftime("%Y-%m-%d") in config.holidays:
        return False

    return True


def move_to_next_working_start(current, config, tz):
    while True:
        current = current + timedelta(days=1)

        if is_working_day(current.date(), config):
            return datetime.combine(
                current.date(),
                ensure_time(config.work_start_time),
                tzinfo=tz
            )


def calculate_due_at(created_at, sla_hours, config):
    tz = ZoneInfo(config.time_zone)

    # ✅ SAFE + TEST FRIENDLY conversion
    if timezone.is_naive(created_at):
        current = created_at.replace(tzinfo=tz)
    else:
        current = created_at.astimezone(tz)

    remaining_seconds = sla_hours * 3600

    work_start = ensure_time(config.work_start_time)
    work_end = ensure_time(config.work_end_time)

    while remaining_seconds > 0:

        if not is_working_day(current.date(), config):
            current = move_to_next_working_start(current, config, tz)
            continue

        start_of_day = datetime.combine(current.date(), work_start, tzinfo=tz)
        end_of_day = datetime.combine(current.date(), work_end, tzinfo=tz)

        if current < start_of_day:
            current = start_of_day

        if current >= end_of_day:
            current = move_to_next_working_start(current, config, tz)
            continue

        available_seconds = int((end_of_day - current).total_seconds())

        if remaining_seconds <= available_seconds:
            return current + timedelta(seconds=remaining_seconds)

        remaining_seconds -= available_seconds
        current = move_to_next_working_start(current, config, tz)

    return current


def update_task_due_at(task_id):

    task = TaskInstance.objects.get(task_id=task_id)

    config = WorkingHoursConfig.objects.first()
    if not config:
        raise Exception("WorkingHoursConfig not found")

    due_at = calculate_due_at(
        created_at=task.created_at,
        sla_hours=task.sla_hours,
        config=config
    )

    TaskInstance.objects.filter(task_id=task_id).update(
        due_at=due_at
    )

    # ❗ SAFE JOB ID
    job_id = f"sla_task_{task.task_id}"

    # remove old job if exists
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)

    # add new job safely
    scheduler.add_job(
        check_sla_status,
        trigger="date",
        run_date=due_at,
        args=[task.task_id],
        id=job_id,
        replace_existing=True
    )

    return due_at