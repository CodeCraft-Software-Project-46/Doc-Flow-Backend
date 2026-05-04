from datetime import timedelta

from sla_engine.utils.working_time import next_working_day_start

def calculate_due_at(created_at, sla_hours, config):
    current_time = created_at
    remaining_minutes = sla_hours * 60

    work_start = config["work_start_time"]
    work_end = config["work_end_time"]
    work_days = config["work_days"]
    holidays = config["holidays"]

    while remaining_minutes > 0:

        # Skip non-working days
        if current_time.weekday() not in work_days or str(current_time.date()) in holidays:
            current_time = next_working_day_start(current_time, work_start)
            continue

        # Adjust start time
        if current_time.time() < work_start:
            current_time = current_time.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0
            )

        if current_time.time() >= work_end:
            current_time = next_working_day_start(current_time, work_start)
            continue

        workday_end = current_time.replace(
            hour=work_end.hour,
            minute=work_end.minute,
            second=0
        )

        available_minutes = int((workday_end - current_time).total_seconds() / 60)

        if remaining_minutes <= available_minutes:
            return current_time + timedelta(minutes=remaining_minutes)

        remaining_minutes -= available_minutes
        current_time = next_working_day_start(current_time, work_start)

    return current_time 