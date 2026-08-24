from django.conf import settings
from django.db import models

from .models import generate_id  # reuse the same id generator as Workflow


class WorkflowSample(models.Model):
    """
    Same shape as Workflow, but points at workflows_workflow_sample —
    the clean hand-seeded table — instead of workflows_workflow.

    managed = False because the table was created directly via SQL
    (create_and_seed_sample_table.sql), not via Django migrations.
    Django will read/write rows in it but will never try to
    create/alter/drop it on `manage.py migrate`.
    """

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Active", "Active"),
        ("Archived", "Archived"),
        ("Deprecated", "Deprecated"),
    ]

    id = models.CharField(
        max_length=32, primary_key=True, default=generate_id, editable=False
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    external_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    document_category = models.CharField(max_length=120, blank=True, default="")
    document_type = models.CharField(max_length=120, blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
    version = models.PositiveIntegerField()

    trigger = models.CharField(max_length=20, blank=True, default="", db_column="trigger")
    trigger_path = models.CharField(max_length=255, blank=True, default="")
    allowed_file_types = models.JSONField(blank=True, default=list)

    definition = models.JSONField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="created_by_id",
    )

    class Meta:
        managed = False
        db_table = "workflows_workflow_sample"
        ordering = ["-version"]

    def __str__(self):
        return f"{self.name} v{self.version}"