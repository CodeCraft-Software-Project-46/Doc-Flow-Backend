from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from analytics.models import TaskInstance
from working_hours.models import WorkingHoursConfig

# This whole file answers one question: "given a task was created at time X,
# and it has Y hours to be done, what is the actual deadline (due_at)?"
# The tricky part is that Y hours means Y *working* hours — nights,
# weekends, and holidays don't count, so the deadline has to skip over them.

# The system only ever runs in Sri Lanka, so the working-hours calendar is
# always interpreted in this timezone rather than a per-config value.
PROJECT_TIME_ZONE = "Asia/Colombo"


def ensure_time(value):
    """
    Convert a stored time value into datetime.time.
    """

    # The work_start_time / work_end_time coming from the database can
    # already be a proper Python time object, or it can be a plain string
    # like "09:00:00". This function accepts either and always hands back
    # a real time object so the rest of the code doesn't have to care which
    # form it started as.

    if value is None:
        raise ValueError(
            "Working time value cannot be None."
        )

    if hasattr(value, "hour"):
        # Already a real time-like object (has an .hour attribute) — nothing to do.
        return value

    if isinstance(value, str):
        value = value.strip()

        # Try the two formats we might realistically see: "09:00:00" and "09:00".
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(
                    value,
                    fmt,
                ).time()
            except ValueError:
                continue

    raise ValueError(
        f"Unsupported time value: {value}"
    )


def is_working_day(date_obj, config):
    """
    Check whether the given date is a configured
    working day and is not a holiday.

    Project convention:

        Sunday    = 0
        Monday    = 1
        Tuesday   = 2
        Wednesday = 3
        Thursday  = 4
        Friday    = 5
        Saturday  = 6
    """

    # Python's own weekday() numbers Monday=0 ... Sunday=6, but this project
    # numbers Sunday=0 ... Saturday=6 instead (see the docstring above).
    # This line converts from Python's numbering to the project's numbering.
    configured_weekday = (
        date_obj.weekday() + 1
    ) % 7

    work_days = config.work_days or []

    # If today's weekday isn't in the list of working days (e.g. it's a
    # Saturday and only Mon-Fri are configured), it's not a working day —
    # no need to even look at the holiday list.
    if configured_weekday not in work_days:
        return False

    date_string = date_obj.strftime(
        "%Y-%m-%d"
    )

    holidays = config.holidays or []

    # Even if today would normally be a working day, a matching holiday
    # date overrides that and makes it a non-working day instead.
    for holiday in holidays:

        if str(holiday)[:10] == date_string:
            return False

    return True


# Safety limit for the loop below. If someone accidentally configures the
# system with zero working days (or every day is a holiday forever), there
# would be no "next working day" to find — without this limit, the search
# would spin forever and freeze whatever process is running it. Raising a
# clear error instead is far better than an invisible hang, especially with
# thousands/millions of tasks relying on this running quickly.
MAX_DAYS_TO_NEXT_WORKING_DAY = 400


def move_to_next_working_start(
    current,
    config,
    tz,
):
    """
    Move to the next configured working day
    at the configured working start time.
    """

    # "Next working start" means: whatever the very next working day is,
    # give me that day at the configured start time (e.g. 9:00 AM). This is
    # what happens when a task's remaining SLA time runs out for today and
    # needs to carry over — possibly skipping a weekend or a holiday (or both)
    # to land on the next real working day.

    work_start = ensure_time(
        config.work_start_time
    )

    next_day = current + timedelta(days=1)

    # Walk forward one day at a time until we land on an actual working day.
    for _ in range(MAX_DAYS_TO_NEXT_WORKING_DAY):

        if is_working_day(
            next_day.date(),
            config,
        ):
            return datetime.combine(
                next_day.date(),
                work_start,
                tzinfo=tz,
            )

        next_day += timedelta(days=1)

    # We looked more than a year ahead and never found a single working day —
    # that means the working-hours configuration itself is broken.
    raise ValueError(
        "No working day found within "
        f"{MAX_DAYS_TO_NEXT_WORKING_DAY} days. "
        "Check WorkingHoursConfig.work_days/holidays."
    )


def calculate_due_at(
    created_at,
    sla_hours,
    config,
):
    """
    Calculate SLA due datetime using:

    - configured working hours
    - configured working days
    - configured holidays
    - fixed project timezone (Asia/Colombo)

    Example:

        Working hours: 09:00 - 17:00
        Working days: Monday-Friday

        Created:
            Friday 16:00

        SLA:
            4 hours

        Result:
            Monday 12:00
    """

    # In plain terms: this function "spends" the SLA hours minute by minute,
    # but only counts minutes that fall inside working hours, on a working
    # day, and not on a holiday. Whenever it runs out of working time for
    # the current day, it jumps forward to the start of the next working
    # day and keeps spending from there — like a countdown that pauses
    # every night, every weekend, and every holiday, and resumes the
    # moment the office reopens.

    if created_at is None:
        raise ValueError(
            "created_at cannot be None."
        )

    if sla_hours is None:
        raise ValueError(
            "sla_hours cannot be None."
        )

    sla_hours = float(sla_hours)

    if sla_hours < 0:
        raise ValueError(
            "sla_hours cannot be negative."
        )

    tz = ZoneInfo(
        PROJECT_TIME_ZONE
    )

    # Make sure we're always working in Sri Lanka time, no matter what
    # timezone (or lack of one) the created_at timestamp arrived in.
    if timezone.is_naive(created_at):
        current = created_at.replace(
            tzinfo=tz
        )
    else:
        current = created_at.astimezone(
            tz
        )

    # Convert the SLA hours into seconds so we can subtract exact chunks
    # of working time as we go (this also lets sla_hours be a fraction,
    # like 0.5 hours = 30 minutes).
    remaining_seconds = (
        sla_hours * 3600
    )

    work_start = ensure_time(
        config.work_start_time
    )

    work_end = ensure_time(
        config.work_end_time
    )

    if work_start >= work_end:
        raise ValueError(
            "work_start_time must be earlier "
            "than work_end_time."
        )

    # Keep going until the whole SLA duration has been "used up" by
    # working time.
    while remaining_seconds > 0:

        # Case 1: today isn't a working day at all (weekend or holiday) —
        # skip straight to the next working day's start time.
        if not is_working_day(
            current.date(),
            config,
        ):
            current = (
                move_to_next_working_start(
                    current,
                    config,
                    tz,
                )
            )
            continue

        start_of_day = datetime.combine(
            current.date(),
            work_start,
            tzinfo=tz,
        )

        end_of_day = datetime.combine(
            current.date(),
            work_end,
            tzinfo=tz,
        )

        # Case 2: it's a working day, but we're starting before opening
        # time (e.g. a task created at 6 AM) — the clock only starts
        # counting once the office actually opens.
        if current < start_of_day:
            current = start_of_day

        # Case 3: it's a working day, but we're already past closing time
        # (e.g. a task created at 8 PM) — nothing left to spend today,
        # so jump to the next working day's start.
        if current >= end_of_day:
            current = (
                move_to_next_working_start(
                    current,
                    config,
                    tz,
                )
            )
            continue

        # How much working time is left today, from right now until closing?
        available_seconds = (
            end_of_day - current
        ).total_seconds()

        # Case 4: the SLA finishes sometime today — we've found the answer.
        if remaining_seconds <= available_seconds:

            return current + timedelta(
                seconds=remaining_seconds
            )

        # Case 5: today's remaining working time isn't enough — use all of
        # it up, then carry the leftover forward to the next working day.
        remaining_seconds -= (
            available_seconds
        )

        current = (
            move_to_next_working_start(
                current,
                config,
                tz,
            )
        )

    return current


def get_working_hours_config():
    """
    Get the latest company working-hours
    configuration.
    """

    # There's only meant to be one working-hours settings row for the whole
    # company (start time, end time, working days, holidays). This grabs
    # the most recently updated one.
    config = (
        WorkingHoursConfig.objects
        .order_by("-updated_at")
        .first()
    )

    if not config:
        raise ValueError(
            "WorkingHoursConfig not found. "
            "Configure working hours first."
        )

    return config


def calculate_task_due_at(task):
    """
    Calculate due_at for a TaskInstance.
    """

    # Small convenience wrapper: look up the current company calendar, then
    # work out this specific task's deadline using it.
    config = get_working_hours_config()

    return calculate_due_at(
        created_at=task.created_at,
        sla_hours=task.sla_hours,
        config=config,
    )


@transaction.atomic
def update_task_due_at(task_id):
    """
    Calculate and persist due_at for a task.
    """

    # select_for_update() locks this task's row so that if two processes
    # try to set its due_at at the exact same moment, they can't both
    # succeed and step on each other — only one wins, safely.
    task = (
        TaskInstance.objects
        .select_for_update()
        .get(task_id=task_id)
    )

    # Both the creation signal and reconciliation may see a new task.  The
    # first caller establishes the immutable SLA deadline; later callers must
    # not recalculate it using a changed company calendar.
    #
    # In plain terms: once a deadline has been worked out for a task, it's
    # locked in forever, even if the working-hours settings change later.
    # This is what stops an existing task's deadline from silently shifting
    # just because someone edited the office hours afterward.
    if task.due_at is not None:
        return task.due_at

    due_at = calculate_task_due_at(
        task
    )

    task.due_at = due_at
    task.save(update_fields=["due_at"])

    return due_at
