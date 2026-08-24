import uuid

from django.conf import settings
from django.db import models


def generate_id():
    # matches the char(32) PK style in the table (uuid4 hex, no dashes)
    return uuid.uuid4().hex


class Workflow(models.Model):
    """
    One row = one *version* of a workflow.
    Rows sharing the same `external_id` are versions of the same logical
    workflow; `version` is the incrementing int for that group.
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    external_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    document_category = models.CharField(max_length=120, blank=True, default="")
    document_type = models.CharField(max_length=120, blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
    version = models.PositiveIntegerField()

    trigger = models.CharField(max_length=20, blank=True, default="")
    trigger_path = models.CharField(max_length=255, blank=True, default="")
    allowed_file_types = models.JSONField(blank=True, default=list)

    # nodes/connections graph — see backend/compare_utils.py for shape
    definition = models.JSONField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflow_versions",
        db_column="created_by_id",
    )

    class Meta:
        db_table = "workflows_workflow"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_id", "version"], name="unique_workflow_version"
            )
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

