from datetime import datetime, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from sla.services.sla_calculator import calculate_due_at

TZ = ZoneInfo("Asia/Colombo")


class SLACalculatorTests(SimpleTestCase):
    def setUp(self):
        self.calendar = SimpleNamespace(
            work_start_time=time(9, 0),
            work_end_time=time(17, 0),
            # Sunday=0, Monday=1, ..., Saturday=6
            work_days=[1, 2, 3, 4, 5],
            holidays=[],
        )

    def test_sla_carries_remaining_time_to_next_working_day(self):
        due_at = calculate_due_at(
            datetime(2026, 8, 21, 16, 0, tzinfo=TZ),
            4,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 24, 12, 0, tzinfo=TZ),
        )

    def test_holiday_is_not_counted_as_working_time(self):
        self.calendar.holidays = ["2026-08-24"]

        due_at = calculate_due_at(
            datetime(2026, 8, 21, 16, 0, tzinfo=TZ),
            4,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 25, 12, 0, tzinfo=TZ),
        )

    def test_before_working_hours_starts_at_workday_start(self):
        due_at = calculate_due_at(
            datetime(2026, 8, 24, 7, 0, tzinfo=TZ),
            2,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 24, 11, 0, tzinfo=TZ),
        )

    def test_empty_work_days_raises_instead_of_hanging(self):
        self.calendar.work_days = []

        with self.assertRaises(ValueError):
            calculate_due_at(
                datetime(2026, 8, 21, 16, 0, tzinfo=TZ),
                4,
                self.calendar,
            )

    def test_weekend_is_skipped(self):
        # Friday 16:30 + 2h -> 30min left Friday, 1.5h remaining ->
        # Saturday/Sunday are not working days -> Monday 09:00 + 1.5h
        due_at = calculate_due_at(
            datetime(2026, 8, 21, 16, 30, tzinfo=TZ),
            2,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 24, 10, 30, tzinfo=TZ),
        )

    def test_created_on_non_working_day_rolls_to_next_working_day(self):
        due_at = calculate_due_at(
            datetime(2026, 8, 22, 14, 0, tzinfo=TZ),  # Saturday
            1,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 24, 10, 0, tzinfo=TZ),
        )

    def test_multi_day_holiday_block_is_skipped(self):
        self.calendar.holidays = ["2026-08-25", "2026-08-26"]

        # Monday 16:30 + 2h -> 30min left Monday, 1.5h remaining ->
        # Tue/Wed are holidays -> Thursday 09:00 + 1.5h
        due_at = calculate_due_at(
            datetime(2026, 8, 24, 16, 30, tzinfo=TZ),
            2,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 27, 10, 30, tzinfo=TZ),
        )

    def test_same_day_no_elimination_needed(self):
        # Monday 10:00 + 2h fits entirely within the same working day ->
        # nothing is eliminated at all.
        due_at = calculate_due_at(
            datetime(2026, 8, 24, 10, 0, tzinfo=TZ),
            2,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 24, 12, 0, tzinfo=TZ),
        )

    def test_multi_day_normal_span_with_no_obstruction(self):
        # Monday 09:00 + 20h: 8h/day capacity, no weekend/holiday in the way.
        # Mon consumes 8h (12h left), Tue consumes 8h (4h left),
        # Wed 09:00 + 4h -> 13:00.
        due_at = calculate_due_at(
            datetime(2026, 8, 24, 9, 0, tzinfo=TZ),
            20,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 26, 13, 0, tzinfo=TZ),
        )

    def test_holiday_adjacent_to_weekend_is_fully_skipped(self):
        self.calendar.holidays = ["2026-08-28"]  # Friday holiday, then weekend

        # Thursday 16:00 + 3h -> 1h left Thursday, 2h remaining ->
        # Friday (holiday) + Sat/Sun (weekend) all skipped -> Monday 09:00 + 2h
        due_at = calculate_due_at(
            datetime(2026, 8, 27, 16, 0, tzinfo=TZ),
            3,
            self.calendar,
        )

        self.assertEqual(
            due_at,
            datetime(2026, 8, 31, 11, 0, tzinfo=TZ),
        )
