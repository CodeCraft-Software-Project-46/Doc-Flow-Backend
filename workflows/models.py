from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def uuid_str() -> str:
    return str(uuid.uuid4())


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Role(TimeStampedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(User, related_name="workflow_roles", blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.CASCADE, related_name="roles")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="unique_role_name_per_department"),
        ]

    def __str__(self) -> str:
        return self.name


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="user_profiles")

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"{self.user.username} profile"


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance: User, created: bool, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Workflow(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_DISABLED = "disabled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
        (STATUS_DISABLED, "Disabled"),
    ]

    TRIGGER_ONEDRIVE = "onedrive"
    TRIGGER_MANUAL = "manual"
    TRIGGER_API = "api"

    TRIGGER_CHOICES = [
        (TRIGGER_ONEDRIVE, "OneDrive"),
        (TRIGGER_MANUAL, "Manual"),
        (TRIGGER_API, "API"),
    ]

    external_id = models.CharField(max_length=64, unique=True, default=uuid_str, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_category = models.CharField(max_length=120, default="general")
    document_type = models.CharField(max_length=120, default="general")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    version = models.PositiveIntegerField(default=1)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default=TRIGGER_MANUAL)
    trigger_path = models.CharField(max_length=255, blank=True)
    allowed_file_types = models.JSONField(default=list, blank=True)
    definition = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_workflows")

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name


class WorkflowNode(TimeStampedModel):
    NODE_START = "start"
    NODE_TASK = "task"
    NODE_DECISION = "decision"
    NODE_MERGE = "merge"
    NODE_PARALLEL_SPLIT = "parallel-split"
    NODE_PARALLEL_JOIN = "parallel-join"
    NODE_END = "end"
    NODE_SUB_WORKFLOW = "sub-workflow"
    NODE_TIMER = "timer"
    NODE_ESCALATION = "escalation"
    NODE_NOTIFICATION = "notification"

    NODE_TYPE_CHOICES = [
        (NODE_START, "Start"),
        (NODE_TASK, "Task"),
        (NODE_DECISION, "Decision"),
        (NODE_MERGE, "Merge"),
        (NODE_PARALLEL_SPLIT, "Parallel Split"),
        (NODE_PARALLEL_JOIN, "Parallel Join"),
        (NODE_END, "End"),
        (NODE_SUB_WORKFLOW, "Sub Workflow"),
        (NODE_TIMER, "Timer"),
        (NODE_ESCALATION, "Escalation"),
        (NODE_NOTIFICATION, "Notification"),
    ]

    workflow = models.ForeignKey(Workflow, related_name="nodes", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=64)
    node_type = models.CharField(max_length=32, choices=NODE_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    assigned_role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="workflow_nodes")

    class Meta:
        ordering = ["position_y", "position_x", "name"]
        constraints = [
            models.UniqueConstraint(fields=["workflow", "external_id"], name="unique_node_external_id_per_workflow"),
        ]

    def __str__(self) -> str:
        return f"{self.workflow.name}::{self.name}"


class WorkflowTransition(TimeStampedModel):
    CONNECTION_APPROVE = "approve"
    CONNECTION_REJECT = "reject"
    CONNECTION_REVISION = "revision"
    CONNECTION_PARALLEL = "parallel"
    CONNECTION_DEFAULT = "default"
    CONNECTION_TIMEOUT = "timeout"
    CONNECTION_ESCALATE = "escalate"

    CONNECTION_TYPE_CHOICES = [
        (CONNECTION_APPROVE, "Approve"),
        (CONNECTION_REJECT, "Reject"),
        (CONNECTION_REVISION, "Revision"),
        (CONNECTION_PARALLEL, "Parallel"),
        (CONNECTION_DEFAULT, "Default"),
        (CONNECTION_TIMEOUT, "Timeout"),
        (CONNECTION_ESCALATE, "Escalate"),
    ]

    workflow = models.ForeignKey(Workflow, related_name="transitions", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=64)
    source_node = models.ForeignKey(WorkflowNode, related_name="outgoing_transitions", on_delete=models.CASCADE)
    target_node = models.ForeignKey(WorkflowNode, related_name="incoming_transitions", on_delete=models.CASCADE)
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPE_CHOICES, default=CONNECTION_DEFAULT)
    label = models.CharField(max_length=255, blank=True)
    condition = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["priority", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["workflow", "external_id"], name="unique_transition_external_id_per_workflow"),
        ]

    def __str__(self) -> str:
        return f"{self.source_node.name} -> {self.target_node.name}"


class WorkflowInstance(TimeStampedModel):
    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FAILED, "Failed"),
    ]

    workflow = models.ForeignKey(Workflow, related_name="instances", on_delete=models.CASCADE)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="started_workflow_instances")
    document_name = models.CharField(max_length=255, blank=True)
    document_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    current_node = models.ForeignKey(WorkflowNode, null=True, blank=True, on_delete=models.SET_NULL, related_name="current_instances")
    current_state = models.CharField(max_length=255, blank=True)
    current_assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="current_workflow_assignments")
    payload = models.JSONField(default=dict, blank=True)
    runtime_state = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.workflow.name} instance"


class NodeInstance(TimeStampedModel):
    STATUS_PENDING = "PENDING"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_WAITING = "WAITING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_SKIPPED = "SKIPPED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_WAITING, "Waiting"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_SKIPPED, "Skipped"),
        (STATUS_FAILED, "Failed"),
    ]

    workflow_instance = models.ForeignKey(WorkflowInstance, related_name="node_instances", on_delete=models.CASCADE)
    workflow_node = models.ForeignKey(WorkflowNode, related_name="runtime_instances", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_node_instances")
    branch_key = models.CharField(max_length=120, blank=True)
    context = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class TaskInstance(TimeStampedModel):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    workflow_instance = models.ForeignKey(WorkflowInstance, related_name="task_instances", on_delete=models.CASCADE)
    node_instance = models.OneToOneField(NodeInstance, related_name="task_instance", on_delete=models.CASCADE)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="task_instances")
    assigned_role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="task_instances")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    action = models.CharField(max_length=40, blank=True)
    comment = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    requires_submission = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    submission_data = models.JSONField(default=dict, blank=True)
    approval_data = models.JSONField(default=dict, blank=True)
    submission_completed_at = models.DateTimeField(null=True, blank=True)
    approval_completed_at = models.DateTimeField(null=True, blank=True)
    sla_minutes = models.IntegerField(default=5)
    sla_seconds = models.IntegerField(default=5)
    sla_exceeded = models.BooleanField(default=False)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Notification(TimeStampedModel):
    TYPE_TASK_ASSIGNED = "task_assigned"
    TYPE_TASK_COMPLETED = "task_completed"
    TYPE_APPROVAL_NEEDED = "approval_needed"
    TYPE_SUBMISSION_NEEDED = "submission_needed"
    TYPE_SLA_WARNING = "sla_warning"
    TYPE_SLA_EXCEEDED = "sla_exceeded"
    TYPE_WORKFLOW_COMPLETED = "workflow_completed"
    TYPE_WORKFLOW_REJECTED = "workflow_rejected"

    TYPE_CHOICES = [
        (TYPE_TASK_ASSIGNED, "Task Assigned"),
        (TYPE_TASK_COMPLETED, "Task Completed"),
        (TYPE_APPROVAL_NEEDED, "Approval Needed"),
        (TYPE_SUBMISSION_NEEDED, "Submission Needed"),
        (TYPE_SLA_WARNING, "SLA Warning"),
        (TYPE_SLA_EXCEEDED, "SLA Exceeded"),
        (TYPE_WORKFLOW_COMPLETED, "Workflow Completed"),
        (TYPE_WORKFLOW_REJECTED, "Workflow Rejected"),
    ]

    workflow_instance = models.ForeignKey(WorkflowInstance, related_name="notifications", on_delete=models.CASCADE)
    task_instance = models.ForeignKey(TaskInstance, null=True, blank=True, related_name="notifications", on_delete=models.CASCADE)
    assigned_role = models.ForeignKey(Role, null=True, blank=True, related_name="notifications", on_delete=models.SET_NULL)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="notifications", on_delete=models.SET_NULL)
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def role_id(self):
        return self.assigned_role_id

    @property
    def is_read(self):
        return self.read