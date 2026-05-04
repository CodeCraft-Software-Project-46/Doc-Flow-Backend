from datetime import timedelta


def next_working_day_start(current_time, work_start):
    next_day = current_time + timedelta(days=1)
    return next_day.replace(
        hour=work_start.hour,
        minute=work_start.minute,
        second=0
    )