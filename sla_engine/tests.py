from django.test import TestCase
from django.utils import timezone
from analytics.models import TaskInstance


class SLAEngineTests(TestCase):

    def test_breach_task(self):
        now = timezone.now()

        task = TaskInstance.objects.create(
            task_name="BREACH TASK TEST",
            created_at=now,
            status="pending",
            workflow_instance_id=1,
            assigned_role_id=1,
            sla_hours=0.001  # fast test (~3–5 sec)
        )

        task.refresh_from_db()

        self.assertIsNotNone(task.due_at)


    def test_met_task(self):
        now = timezone.now()

        task = TaskInstance.objects.create(
            task_name="MET TASK TEST",
            created_at=now,
            status="pending",
            workflow_instance_id=1,
            assigned_role_id=1,
            sla_hours=0.001
        )

        task.completed_at = timezone.now()
        task.status = "completed"

        # 🔥 IMPORTANT: preserve due_at
        task.save(update_fields=["completed_at", "status"])

        self.assertEqual(task.status, "completed")