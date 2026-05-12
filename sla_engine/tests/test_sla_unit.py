import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from datetime import timedelta, datetime, timezone as dt_timezone

# Provide lightweight fake modules so importing sla_calculator doesn't require Django setup
fake_analytics_models = types.ModuleType("analytics.models")
fake_analytics_models.TaskInstance = SimpleNamespace(
    objects=SimpleNamespace(
        get=lambda *a, **k: None,
        filter=lambda *a, **k: SimpleNamespace(update=lambda **kwargs: 1),
    )
)
sys.modules["analytics.models"] = fake_analytics_models

fake_working_hours = types.ModuleType("working_hours.models")
fake_working_hours.WorkingHoursConfig = SimpleNamespace(objects=SimpleNamespace(first=lambda: None))
sys.modules["working_hours.models"] = fake_working_hours

from sla_engine.services import sla_calculator
from sla_engine import scheduler as sla_scheduler


class SLAMockTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(dt_timezone.utc)

    @patch("sla_engine.scheduler.scheduler.add_job")
    @patch("working_hours.models.WorkingHoursConfig.objects.first")
    @patch("analytics.models.TaskInstance.objects.get")
    def test_update_task_due_at_schedules(self, mock_get, mock_config_first, mock_add_job):
        # fake config
        cfg = SimpleNamespace(
            work_start_time="00:00:00",
            work_end_time="23:59:00",
            work_days=[1, 2, 3, 4, 5],
            holidays=[],
            time_zone="UTC",
        )
        mock_config_first.return_value = cfg

        # fake task object with save method
        task = SimpleNamespace(
            task_id=123,
            created_at=self.now,
            sla_hours=0.066,
            due_at=None,
            save=lambda update_fields=None: None,
        )

        mock_get.return_value = task

        due = sla_calculator.update_task_due_at(task.task_id)

        # due_at should be returned and scheduler.add_job should be called
        mock_add_job.assert_called()
        self.assertIsNotNone(due)

    @patch("sla_engine.scheduler.close_old_connections")
    @patch("sla_engine.scheduler.timezone.now", return_value=datetime.now(dt_timezone.utc))
    @patch("analytics.models.TaskInstance.objects.filter")
    @patch("analytics.models.TaskInstance.objects.get")
    def test_check_sla_status_sets_breached(self, mock_get, mock_filter, mock_tz_now, mock_close_old_connections):
        # Task not completed and due_at past
        task = MagicMock()
        task.task_id = 200
        task.due_at = self.now - timedelta(seconds=5)
        task.completed_at = None
        # ensure get returns the same mock for both calls
        mock_get.return_value = task
        mock_filter.return_value.update.return_value = 1

        sla_scheduler.check_sla_status(task.task_id)

        mock_filter.return_value.update.assert_called_once_with(sla_status="breached")


if __name__ == "__main__":
    unittest.main()
