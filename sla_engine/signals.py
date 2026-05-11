from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from analytics.models import TaskInstance
from sla_engine.services.sla_calculator import update_task_due_at
from sla_engine.services.sla_service import evaluate_sla


@receiver(post_save, sender=TaskInstance)
def auto_calculate_due_at(sender, instance, created, **kwargs):

    if kwargs.get("raw"):
        return

    if created:
        transaction.on_commit(
            lambda: update_task_due_at(instance.task_id)
        )