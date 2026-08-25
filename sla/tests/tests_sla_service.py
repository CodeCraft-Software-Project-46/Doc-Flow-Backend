from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from analytics.models import TaskInstance

from sla.services.sla_service import (
    resolve_sla_status,
    evaluate_sla,
)


class SLASchedulingTests(TestCase):

    def create_task(
        self,
        *,
        due_at,
        completed_at=None,
        status="pending",
    ):

        now = timezone.now()

        return TaskInstance.objects.create(
            workflow_instance_id=1,
            created_at=now,
            sla_hours=4,
            due_at=due_at,
            completed_at=completed_at,
            status=status,
        )

    def test_completed_before_due_is_met(self):

        due_at = timezone.now() + timedelta(hours=2)

        completed_at = (
            due_at - timedelta(minutes=30)
        )

        task = self.create_task(
            due_at=due_at,
            completed_at=completed_at,
            status="completed",
        )

        result = resolve_sla_status(task)

        self.assertEqual(
            result,
            "met",
        )

    def test_completed_exactly_at_due_is_met(self):

        due_at = timezone.now()

        task = self.create_task(
            due_at=due_at,
            completed_at=due_at,
            status="completed",
        )

        result = resolve_sla_status(
            task,
            now=due_at,
        )

        self.assertEqual(
            result,
            "met",
        )

    def test_completed_after_due_is_breached(self):

        due_at = timezone.now()

        completed_at = (
            due_at + timedelta(minutes=5)
        )

        task = self.create_task(
            due_at=due_at,
            completed_at=completed_at,
            status="completed",
        )

        result = resolve_sla_status(
            task,
            now=completed_at,
        )

        self.assertEqual(
            result,
            "breached",
        )

    def test_not_completed_at_due_is_breached(self):

        due_at = timezone.now()

        task = self.create_task(
            due_at=due_at,
            completed_at=None,
            status="pending",
        )

        result = resolve_sla_status(
            task,
            now=due_at,
        )

        self.assertEqual(
            result,
            "breached",
        )

    def test_not_completed_before_due_is_none(self):

        due_at = (
            timezone.now()
            + timedelta(hours=1)
        )

        task = self.create_task(
            due_at=due_at,
            completed_at=None,
            status="pending",
        )

        result = resolve_sla_status(
            task,
            now=timezone.now(),
        )

        self.assertIsNone(
            result
        )

    def test_evaluate_sla_persists_met(self):

        due_at = timezone.now()

        completed_at = (
            due_at - timedelta(minutes=10)
        )

        task = self.create_task(
            due_at=due_at,
            completed_at=completed_at,
            status="completed",
        )

        result = evaluate_sla(
            task.task_id,
            evaluation_time=due_at,
        )

        self.assertEqual(
            result,
            "met",
        )

        task.refresh_from_db()

        self.assertEqual(
            task.sla_status,
            "met",
        )

    def test_evaluate_sla_persists_breached(self):

        due_at = timezone.now()

        task = self.create_task(
            due_at=due_at,
            completed_at=None,
            status="pending",
        )

        result = evaluate_sla(
            task.task_id,
            evaluation_time=due_at,
        )

        self.assertEqual(
            result,
            "breached",
        )

        task.refresh_from_db()

        self.assertEqual(
            task.sla_status,
            "breached",
        )