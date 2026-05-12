from django.db.models.signals import post_save
from django.dispatch import receiver

from analytics.models import TaskInstance
from sla_engine.services.sla_calculator import update_task_due_at


@receiver(post_save, sender=TaskInstance)
def auto_calculate_due_at(sender, instance, created, **kwargs):

    if kwargs.get("raw"):
        return

    # ❗ On CREATE: schedule due_at calculation and job
    if created:
        instance.due_at = update_task_due_at(instance.task_id)