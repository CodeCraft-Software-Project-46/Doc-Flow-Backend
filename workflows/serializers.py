from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Department, NodeInstance, Notification, Role, TaskInstance, UserProfile, Workflow, WorkflowInstance, WorkflowNode, WorkflowTransition
from .services import save_workflow_definition, start_workflow_instance, submit_task


class PositionSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.IntegerField()


class WorkflowNodeWriteSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=[choice[0] for choice in WorkflowNode.NODE_TYPE_CHOICES])
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    position = PositionSerializer()
    config = serializers.JSONField(required=False, default=dict)
    assignedRoleId = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")


class WorkflowTransitionWriteSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True)
    sourceNodeId = serializers.CharField()
    targetNodeId = serializers.CharField()
    type = serializers.ChoiceField(choices=[choice[0] for choice in WorkflowTransition.CONNECTION_TYPE_CHOICES], required=False, default=WorkflowTransition.CONNECTION_DEFAULT)
    label = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    condition = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    isDefault = serializers.BooleanField(required=False, default=False)
    priority = serializers.IntegerField(required=False, default=0)
    meta = serializers.JSONField(required=False, default=dict)


class WorkflowDefinitionWriteSerializer(serializers.Serializer):
    workflowId = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    version = serializers.IntegerField(required=False, default=1)
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    documentCategory = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="general")
    documentType = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="general")
    status = serializers.ChoiceField(choices=[choice[0] for choice in Workflow.STATUS_CHOICES], required=False, default=Workflow.STATUS_DRAFT)
    trigger = serializers.ChoiceField(choices=[choice[0] for choice in Workflow.TRIGGER_CHOICES], required=False, default=Workflow.TRIGGER_MANUAL)
    triggerPath = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    allowedFileTypes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    nodes = WorkflowNodeWriteSerializer(many=True, required=False, default=list)
    connections = WorkflowTransitionWriteSerializer(many=True, required=False, default=list)
    transitions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    conditions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    sla = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    approvalRules = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    escalationRules = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Backward/compat support: frontend builder may send `transitions` with from/to.
        if not attrs.get("connections") and attrs.get("transitions"):
            converted_connections: list[dict[str, Any]] = []
            for item in attrs.get("transitions", []):
                converted_connections.append(
                    {
                        "id": item.get("id"),
                        "sourceNodeId": item.get("sourceNodeId") or item.get("from"),
                        "targetNodeId": item.get("targetNodeId") or item.get("to"),
                        "type": item.get("type", WorkflowTransition.CONNECTION_DEFAULT),
                        "label": item.get("label", ""),
                        "condition": item.get("condition", ""),
                        "isDefault": bool(item.get("isDefault", False)),
                        "priority": int(item.get("priority") or 0),
                        "meta": item.get("meta", {}) or {},
                    }
                )
            attrs["connections"] = converted_connections
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Workflow:
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        return save_workflow_definition(validated_data, created_by=user)

    def update(self, instance: Workflow, validated_data: dict[str, Any]) -> Workflow:
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        validated_data.setdefault("workflowId", instance.external_id)
        return save_workflow_definition(validated_data, created_by=user or instance.created_by)


class WorkflowNodeReadSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    id = serializers.CharField(source="external_id")
    type = serializers.CharField(source="node_type")
    position = serializers.SerializerMethodField()
    assignedRoleId = serializers.CharField(source="assigned_role_id", allow_null=True, required=False)

    class Meta:
        model = WorkflowNode
        fields = ["uuid", "id", "type", "name", "description", "position", "config", "assignedRoleId"]

    def get_position(self, obj: WorkflowNode) -> dict[str, int]:
        return {"x": obj.position_x, "y": obj.position_y}


class WorkflowTransitionReadSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    id = serializers.CharField(source="external_id")
    sourceNodeId = serializers.CharField(source="source_node.external_id")
    targetNodeId = serializers.CharField(source="target_node.external_id")
    type = serializers.CharField(source="connection_type")
    isDefault = serializers.BooleanField(source="is_default")

    class Meta:
        model = WorkflowTransition
        fields = ["uuid", "id", "sourceNodeId", "targetNodeId", "type", "label", "condition", "isDefault", "priority", "meta"]


class WorkflowReadSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    workflowId = serializers.CharField(source="external_id", read_only=True)
    documentCategory = serializers.CharField(source="document_category")
    documentType = serializers.CharField(source="document_type")
    triggerPath = serializers.CharField(source="trigger_path")
    allowedFileTypes = serializers.ListField(source="allowed_file_types", child=serializers.CharField())
    createdBy = serializers.CharField(source="created_by.username", allow_null=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    nodes = WorkflowNodeReadSerializer(many=True, read_only=True)
    connections = WorkflowTransitionReadSerializer(many=True, read_only=True, source="transitions")

    class Meta:
        model = Workflow
        fields = [
            "uuid",
            "workflowId",
            "name",
            "description",
            "documentCategory",
            "documentType",
            "status",
            "version",
            "trigger",
            "triggerPath",
            "allowedFileTypes",
            "definition",
            "createdBy",
            "createdAt",
            "updatedAt",
            "nodes",
            "connections",
        ]


class RoleSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    departmentId = serializers.CharField(source="department_id", allow_null=True, read_only=True)
    departmentName = serializers.CharField(source="department.name", allow_null=True, read_only=True)

    class Meta:
        model = Role
        fields = ["uuid", "id", "name", "description", "departmentId", "departmentName"]


class DepartmentSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Department
        fields = ["uuid", "id", "name"]


class UserProfileSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    roleId = serializers.CharField(source="role_id", allow_null=True, read_only=True)
    roleName = serializers.CharField(source="role.name", allow_null=True, read_only=True)
    departmentId = serializers.CharField(source="role.department_id", allow_null=True, read_only=True)
    departmentName = serializers.CharField(source="role.department.name", allow_null=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = ["id", "userId", "username", "roleId", "roleName", "departmentId", "departmentName"]


class WorkflowStartSerializer(serializers.Serializer):
    documentName = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    documentType = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    payload = serializers.JSONField(required=False, default=dict)


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    workflowId = serializers.CharField(source="workflow.external_id", read_only=True)
    workflowName = serializers.CharField(source="workflow.name", read_only=True)
    documentName = serializers.CharField(source="document_name")
    documentType = serializers.CharField(source="document_type")
    currentStep = serializers.CharField(source="current_state", allow_blank=True)
    currentAssignee = serializers.CharField(source="current_assignee.username", allow_null=True, read_only=True)
    startedAt = serializers.DateTimeField(source="started_at", read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)
    runtimeState = serializers.JSONField(source="runtime_state", read_only=True)
    payload = serializers.JSONField(read_only=True)
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "uuid",
            "workflowId",
            "workflowName",
            "documentName",
            "documentType",
            "status",
            "currentStep",
            "currentAssignee",
            "startedAt",
            "completedAt",
            "runtimeState",
            "payload",
            "timeline",
        ]

    def get_timeline(self, obj: WorkflowInstance) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        started_actor = obj.started_by.username if obj.started_by else "System"
        events.append(
            {
                "id": f"workflow-started-{obj.id}",
                "action": "Workflow Started",
                "actor": started_actor,
                "timestamp": obj.started_at,
                "comment": None,
                "attachments": [],
            }
        )

        node_instances = (
            obj.node_instances.select_related("workflow_node", "task_instance", "task_instance__assigned_role", "task_instance__assigned_user")
            .order_by("created_at")
        )

        for node_instance in node_instances:
            node = node_instance.workflow_node
            created_at = node_instance.started_at or node_instance.created_at
            events.append(
                {
                    "id": f"node-started-{node_instance.id}",
                    "action": f"{node.name} Started",
                    "actor": "System",
                    "timestamp": created_at,
                    "comment": None,
                    "attachments": [],
                }
            )

            task_instance = getattr(node_instance, "task_instance", None)
            if task_instance is not None:
                assigned_actor = (
                    task_instance.assigned_user.username
                    if task_instance.assigned_user
                    else task_instance.assigned_role.name if task_instance.assigned_role else "System"
                )
                events.append(
                    {
                        "id": f"task-assigned-{task_instance.id}",
                        "action": f"{node.name} Assigned",
                        "actor": assigned_actor,
                        "timestamp": node_instance.started_at or node_instance.created_at,
                        "comment": None,
                        "attachments": [],
                    }
                )

                if task_instance.completed_at:
                    action_map = {
                        "approve": "Task Approved",
                        "reject": "Task Rejected",
                        "complete": "Task Completed",
                    }
                    events.append(
                        {
                            "id": f"task-completed-{task_instance.id}",
                            "action": action_map.get(task_instance.action, "Task Updated"),
                            "actor": assigned_actor,
                            "timestamp": task_instance.completed_at,
                            "comment": task_instance.comment or None,
                            "attachments": [],
                        }
                    )
            elif node_instance.completed_at:
                events.append(
                    {
                        "id": f"node-completed-{node_instance.id}",
                        "action": f"{node.name} Completed",
                        "actor": "System",
                        "timestamp": node_instance.completed_at,
                        "comment": None,
                        "attachments": [],
                    }
                )

        if obj.completed_at:
            events.append(
                {
                    "id": f"workflow-completed-{obj.id}",
                    "action": "Workflow Completed",
                    "actor": "System",
                    "timestamp": obj.completed_at,
                    "comment": None,
                    "attachments": [],
                }
            )

        return sorted(events, key=lambda item: item["timestamp"])


class TaskInstanceSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    workflowId = serializers.CharField(source="workflow_instance.workflow.external_id", read_only=True)
    workflowName = serializers.CharField(source="workflow_instance.workflow.name", read_only=True)
    workflowInstance = serializers.CharField(source="workflow_instance.id", read_only=True)
    nodeInstance = serializers.CharField(source="node_instance.id", read_only=True)
    documentName = serializers.CharField(source="workflow_instance.document_name", read_only=True)
    documentType = serializers.CharField(source="workflow_instance.document_type", read_only=True)
    currentStep = serializers.CharField(source="node_instance.workflow_node.name", read_only=True)
    nodeType = serializers.CharField(source="node_instance.workflow_node.node_type", read_only=True)
    assignedUser = serializers.CharField(source="assigned_user.username", allow_null=True, read_only=True)
    assignedRole = serializers.CharField(source="assigned_role.name", allow_null=True, read_only=True)
    assignedRoleId = serializers.CharField(source="assigned_role_id", allow_null=True, read_only=True)
    requiresSubmission = serializers.BooleanField(source="requires_submission", read_only=True)
    requiresApproval = serializers.BooleanField(source="requires_approval", read_only=True)
    submissionData = serializers.JSONField(source="submission_data", read_only=True)
    approvalData = serializers.JSONField(source="approval_data", read_only=True)
    slaSeconds = serializers.IntegerField(source="sla_seconds", read_only=True)
    slaExceeded = serializers.BooleanField(source="sla_exceeded", read_only=True)
    status = serializers.SerializerMethodField()
    startedAt = serializers.DateTimeField(source="node_instance.started_at", read_only=True)
    dueAt = serializers.DateTimeField(source="due_at", allow_null=True, read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", allow_null=True, read_only=True)

    def get_status(self, obj: TaskInstance) -> str:
        return obj.status.lower()

    class Meta:
        model = TaskInstance
        fields = [
            "uuid",
            "workflowId",
            "workflowName",
            "workflowInstance",
            "nodeInstance",
            "documentName",
            "documentType",
            "currentStep",
            "nodeType",
            "assignedUser",
            "assignedRole",
            "assignedRoleId",
            "status",
            "action",
            "comment",
            "payload",
            "requiresSubmission",
            "requiresApproval",
            "submissionData",
            "approvalData",
            "slaSeconds",
            "slaExceeded",
            "startedAt",
            "dueAt",
            "completedAt",
        ]


class TaskSubmissionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "complete"])
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    payload = serializers.JSONField(required=False, default=dict)

    def update(self, instance: TaskInstance, validated_data: dict[str, Any]) -> TaskInstance:
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        return submit_task(
            instance,
            action=validated_data["action"],
            comment=validated_data.get("comment", ""),
            payload=validated_data.get("payload", {}),
            user=user,
        )


class WorkflowStatusSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    workflowId = serializers.CharField(source="workflow.external_id", read_only=True)
    workflowName = serializers.CharField(source="workflow.name", read_only=True)
    currentStep = serializers.CharField(source="current_state", allow_blank=True)
    currentAssignee = serializers.CharField(source="current_assignee.username", allow_null=True, read_only=True)
    startedAt = serializers.DateTimeField(source="started_at", read_only=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = ["uuid", "workflowId", "workflowName", "status", "currentStep", "currentAssignee", "startedAt", "completedAt", "runtime_state", "payload"]


class NotificationSerializer(serializers.ModelSerializer):
    roleId = serializers.CharField(source="assigned_role_id", allow_null=True, read_only=True)
    taskId = serializers.CharField(source="task_instance_id", allow_null=True, read_only=True)
    workflowInstanceId = serializers.CharField(source="workflow_instance_id", read_only=True)
    isRead = serializers.BooleanField(source="read", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "roleId",
            "taskId",
            "workflowInstanceId",
            "notification_type",
            "title",
            "message",
            "data",
            "isRead",
            "created_at",
        ]


class WorkflowListSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    workflowId = serializers.CharField(source="external_id", read_only=True)
    documentCategory = serializers.CharField(source="document_category")
    documentType = serializers.CharField(source="document_type")
    triggerPath = serializers.CharField(source="trigger_path")
    allowedFileTypes = serializers.ListField(source="allowed_file_types", child=serializers.CharField())
    createdBy = serializers.CharField(source="created_by.username", allow_null=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Workflow
        fields = [
            "uuid",
            "workflowId",
            "name",
            "description",
            "documentCategory",
            "documentType",
            "status",
            "version",
            "trigger",
            "triggerPath",
            "allowedFileTypes",
            "createdBy",
            "createdAt",
            "updatedAt",
        ]