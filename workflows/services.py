from __future__ import annotations

import ast
from datetime import timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from .models import NodeInstance, Notification, Role, TaskInstance, Workflow, WorkflowInstance, WorkflowNode, WorkflowTransition


class WorkflowConditionError(ValueError):
    pass


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_evaluate_condition(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a small boolean expression against a workflow payload safely."""

    if not expression or not expression.strip():
        return True

    tree = ast.parse(expression, mode="eval")

    def resolve(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return resolve(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return resolve(node.left) + resolve(node.right)
        if isinstance(node, ast.BoolOp):
            values = [bool(resolve(value)) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(resolve(node.operand))
        if isinstance(node, ast.Compare):
            left = resolve(node.left)
            for operator, comparator in zip(node.ops, node.comparators):
                right = resolve(comparator)
                if isinstance(operator, ast.Eq) and not (left == right):
                    return False
                if isinstance(operator, ast.NotEq) and not (left != right):
                    return False
                if isinstance(operator, ast.Gt) and not (left > right):
                    return False
                if isinstance(operator, ast.GtE) and not (left >= right):
                    return False
                if isinstance(operator, ast.Lt) and not (left < right):
                    return False
                if isinstance(operator, ast.LtE) and not (left <= right):
                    return False
                if isinstance(operator, ast.In) and not (left in right):
                    return False
                if isinstance(operator, ast.NotIn) and not (left not in right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Subscript):
            base = resolve(node.value)
            index = resolve(node.slice)
            return base[index]
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            if isinstance(base, dict):
                return base.get(node.attr)
            return getattr(base, node.attr)
        if isinstance(node, ast.List):
            return [resolve(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(resolve(item) for item in node.elts)
        raise WorkflowConditionError(f"Unsupported expression element: {type(node).__name__}")

    try:
        return bool(resolve(tree))
    except Exception as exc:  # pragma: no cover - defensive guard around user-authored expressions
        raise WorkflowConditionError(str(exc)) from exc


def build_context(*, workflow_instance: WorkflowInstance, node_instance: NodeInstance | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {}
    context.update(_as_dict(workflow_instance.payload))
    context.update(_as_dict(workflow_instance.runtime_state.get("payload")))
    if node_instance is not None:
        context.update(_as_dict(node_instance.context))
    context.update(_as_dict(payload))
    return context


def _node_completion_ids(instance: WorkflowInstance) -> set[str]:
    completed = instance.runtime_state.get("completed_node_ids", [])
    return set(completed if isinstance(completed, list) else [])


def _record_node_completion(instance: WorkflowInstance, node: WorkflowNode) -> None:
    completed = list(_node_completion_ids(instance))
    if node.external_id not in completed:
        completed.append(node.external_id)
    instance.runtime_state["completed_node_ids"] = completed
    instance.save(update_fields=["runtime_state", "updated_at"])


def _mark_task_completed(task_instance: TaskInstance, action: str, comment: str = "", payload: dict[str, Any] | None = None) -> None:
    now = timezone.now()
    task_instance.action = action
    task_instance.comment = comment
    task_instance.payload = payload or {}
    task_instance.completed_at = now

    if action == "reject":
        task_instance.status = TaskInstance.STATUS_REJECTED
        task_instance.node_instance.status = NodeInstance.STATUS_FAILED
        if task_instance.requires_approval:
            task_instance.approval_data = payload or {}
            task_instance.approval_completed_at = now
    elif action in {"approve", "complete"}:
        task_instance.status = TaskInstance.STATUS_APPROVED if action == "approve" else TaskInstance.STATUS_COMPLETED
        task_instance.node_instance.status = NodeInstance.STATUS_COMPLETED
        if action == "approve" and task_instance.requires_approval:
            task_instance.approval_data = payload or {}
            task_instance.approval_completed_at = now
        if action == "complete" and task_instance.requires_submission:
            task_instance.submission_data = payload or {}
            task_instance.submission_completed_at = now
    else:
        task_instance.status = TaskInstance.STATUS_COMPLETED
        task_instance.node_instance.status = NodeInstance.STATUS_COMPLETED

    task_instance.node_instance.completed_at = now
    task_instance.node_instance.save(update_fields=["status", "completed_at", "updated_at"])
    task_instance.save(
        update_fields=[
            "status",
            "action",
            "comment",
            "payload",
            "completed_at",
            "submission_data",
            "approval_data",
            "submission_completed_at",
            "approval_completed_at",
            "updated_at",
        ]
    )


def _resolve_task_requirements(node: WorkflowNode) -> tuple[bool, bool]:
    config = node.config if isinstance(node.config, dict) else {}

    if "requiresSubmission" in config or "requiresApproval" in config:
        return bool(config.get("requiresSubmission")), bool(config.get("requiresApproval"))

    allowed_actions = config.get("allowedActions")
    if isinstance(allowed_actions, list) and allowed_actions:
        return ("submission" in allowed_actions, "approval" in allowed_actions)

    return True, True


def _resolve_task_sla_seconds(node: WorkflowNode) -> int:
    config = node.config if isinstance(node.config, dict) else {}
    if config.get("slaSeconds") is not None:
        try:
            return max(1, int(config.get("slaSeconds")))
        except (TypeError, ValueError):
            return 5

    if config.get("slaHours") is not None:
        try:
            return max(1, int(float(config.get("slaHours")) * 3600))
        except (TypeError, ValueError):
            return 5

    return 5


def _create_task_notification(task: TaskInstance) -> None:
    if not task.assigned_role_id:
        return

    Notification.objects.create(
        workflow_instance=task.workflow_instance,
        task_instance=task,
        assigned_role=task.assigned_role,
        notification_type=Notification.TYPE_TASK_ASSIGNED,
        title="New Task Assigned",
        message="New task assigned",
        data={
            "taskId": str(task.id),
            "workflowInstanceId": str(task.workflow_instance.id),
            "roleId": str(task.assigned_role_id),
        },
    )


def refresh_task_sla(task_instance: TaskInstance) -> TaskInstance:
    if task_instance.status in {TaskInstance.STATUS_APPROVED, TaskInstance.STATUS_REJECTED, TaskInstance.STATUS_COMPLETED, TaskInstance.STATUS_CANCELLED}:
        return task_instance

    threshold_seconds = task_instance.sla_seconds or max(1, int((task_instance.sla_minutes or 1) * 60))
    exceeded = timezone.now() > (task_instance.created_at + timedelta(seconds=threshold_seconds))
    if exceeded and not task_instance.sla_exceeded:
        task_instance.sla_exceeded = True
        task_instance.save(update_fields=["sla_exceeded", "updated_at"])

    return task_instance


def _select_next_transition(node: WorkflowNode, context: dict[str, Any]) -> WorkflowTransition | None:
    outgoing = list(node.outgoing_transitions.all())
    if not outgoing:
        return None

    ordered = sorted(outgoing, key=lambda item: (item.priority, item.created_at))
    default_transition = next((item for item in ordered if item.is_default or item.connection_type == WorkflowTransition.CONNECTION_DEFAULT), None)

    for transition in ordered:
        if transition is default_transition:
            continue
        if safe_evaluate_condition(transition.condition, context):
            return transition

    return default_transition or ordered[0]


def _get_incoming_nodes(node: WorkflowNode) -> list[WorkflowNode]:
    return [transition.source_node for transition in node.incoming_transitions.select_related("source_node")]


def _can_release_join(instance: WorkflowInstance, node: WorkflowNode) -> bool:
    if node.node_type == WorkflowNode.NODE_PARALLEL_JOIN:
        incoming_nodes = _get_incoming_nodes(node)
        completed_ids = _node_completion_ids(instance)
        return all(incoming.external_id in completed_ids for incoming in incoming_nodes)

    if node.node_type == WorkflowNode.NODE_MERGE:
        incoming_nodes = _get_incoming_nodes(node)
        completed_ids = _node_completion_ids(instance)
        return any(incoming.external_id in completed_ids for incoming in incoming_nodes)

    return True


def _release_waiting_nodes(instance: WorkflowInstance) -> None:
    waiting_nodes = NodeInstance.objects.filter(
        workflow_instance=instance,
        status=NodeInstance.STATUS_WAITING,
        workflow_node__node_type__in=[WorkflowNode.NODE_PARALLEL_JOIN, WorkflowNode.NODE_MERGE],
    ).select_related("workflow_node")
    for node_instance in waiting_nodes:
        if _can_release_join(instance, node_instance.workflow_node):
            advance_node_instance(node_instance, build_context(workflow_instance=instance, node_instance=node_instance, payload=instance.payload))


def _create_node_instance(
    *,
    workflow_instance: WorkflowInstance,
    workflow_node: WorkflowNode,
    branch_key: str = "",
    context: dict[str, Any] | None = None,
    assigned_user: User | None = None,
) -> NodeInstance:
    return NodeInstance.objects.create(
        workflow_instance=workflow_instance,
        workflow_node=workflow_node,
        status=NodeInstance.STATUS_ACTIVE,
        branch_key=branch_key,
        context=context or {},
        assigned_user=assigned_user,
        started_at=timezone.now(),
    )


def _create_task_instance(node_instance: NodeInstance, role: Role | None = None, assigned_user: User | None = None) -> TaskInstance:
    existing = TaskInstance.objects.filter(node_instance=node_instance).first()
    if existing:
        return existing

    workflow_instance = node_instance.workflow_instance
    node = node_instance.workflow_node
    config = node.config if isinstance(node.config, dict) else {}

    inherited_role = None
    inherited_role_id = workflow_instance.runtime_state.get("start_assigned_role_id")
    if inherited_role_id and not role:
        inherited_role = Role.objects.filter(id=inherited_role_id).first()

    final_role = role or node.assigned_role or inherited_role
    requires_submission, requires_approval = _resolve_task_requirements(node)
    sla_seconds = _resolve_task_sla_seconds(node)
    due_at = timezone.now() + timedelta(seconds=sla_seconds)

    try:
        task = TaskInstance.objects.create(
            workflow_instance=node_instance.workflow_instance,
            node_instance=node_instance,
            assigned_role=final_role,
            assigned_user=assigned_user,
            requires_submission=requires_submission,
            requires_approval=requires_approval,
            sla_seconds=sla_seconds,
            sla_minutes=max(1, int(sla_seconds / 60)),
            due_at=due_at,
        )
    except IntegrityError:
        return TaskInstance.objects.get(node_instance=node_instance)

    _create_task_notification(task)
    return task


@transaction.atomic
def save_workflow_definition(payload: dict[str, Any], *, created_by: User | None = None) -> Workflow:
    workflow_external_id = payload.get("workflowId") or payload.get("workflow_id") or uuid4_hex()
    defaults = {
        "name": payload.get("name", "Untitled Workflow"),
        "description": payload.get("description", ""),
        "document_category": payload.get("documentCategory", payload.get("document_category", "general")),
        "document_type": payload.get("documentType", payload.get("document_type", "general")),
        "status": payload.get("status", Workflow.STATUS_DRAFT),
        "version": payload.get("version", 1),
        "trigger": payload.get("trigger", Workflow.TRIGGER_MANUAL),
        "trigger_path": payload.get("triggerPath", payload.get("trigger_path", "")) or "",
        "allowed_file_types": payload.get("allowedFileTypes", payload.get("allowed_file_types", [])) or [],
        "definition": payload,
        "created_by": created_by,
    }

    workflow, _ = Workflow.objects.update_or_create(external_id=workflow_external_id, defaults=defaults)

    WorkflowNode.objects.filter(workflow=workflow).delete()

    node_lookup: dict[str, WorkflowNode] = {}
    for node_payload in payload.get("nodes", []):
        role = None
        config_payload = node_payload.get("config", {}) or {}
        role_id = (
            node_payload.get("assignedRoleId")
            or config_payload.get("assigneeId")
            or config_payload.get("triggerRoleId")
        )
        if role_id:
            role = Role.objects.filter(id=role_id).first()

        position = node_payload.get("position", {}) or {}
        node = WorkflowNode.objects.create(
            workflow=workflow,
            external_id=node_payload.get("id") or uuid4_hex(),
            node_type=node_payload.get("type", WorkflowNode.NODE_TASK),
            name=node_payload.get("name", "Untitled Node"),
            description=node_payload.get("description", "") or "",
            position_x=int(position.get("x", 0)),
            position_y=int(position.get("y", 0)),
            config=node_payload.get("config", {}) or {},
            assigned_role=role,
        )
        node_lookup[node.external_id] = node

    for transition_payload in payload.get("connections", payload.get("transitions", [])):
        source = node_lookup.get(transition_payload.get("sourceNodeId") or transition_payload.get("from"))
        target = node_lookup.get(transition_payload.get("targetNodeId") or transition_payload.get("to"))
        if not source or not target:
            continue

        WorkflowTransition.objects.create(
            workflow=workflow,
            external_id=transition_payload.get("id") or uuid4_hex(),
            source_node=source,
            target_node=target,
            connection_type=transition_payload.get("type", WorkflowTransition.CONNECTION_DEFAULT),
            label=transition_payload.get("label", "") or "",
            condition=transition_payload.get("condition", "") or "",
            is_default=bool(transition_payload.get("isDefault", False)),
            priority=int(transition_payload.get("priority") or 0),
            meta=transition_payload.get("meta", {}) or {},
        )

    return workflow


def uuid4_hex() -> str:
    import uuid

    return uuid.uuid4().hex


@transaction.atomic
def start_workflow_instance(
    workflow: Workflow,
    *,
    started_by: User | None = None,
    payload: dict[str, Any] | None = None,
    document_name: str = "",
    document_type: str = "",
) -> WorkflowInstance:
    start_node = workflow.nodes.filter(node_type=WorkflowNode.NODE_START).first()
    instance = WorkflowInstance.objects.create(
        workflow=workflow,
        started_by=started_by,
        document_name=document_name or workflow.name,
        document_type=document_type or workflow.document_type,
        status=WorkflowInstance.STATUS_RUNNING,
        current_node=start_node,
        current_state=start_node.name if start_node else "",
        payload=payload or {},
        runtime_state={"completed_node_ids": [], "payload": payload or {}},
    )

    if start_node is not None:
        node_instance = _create_node_instance(workflow_instance=instance, workflow_node=start_node, context=payload or {}, assigned_user=started_by)
        advance_node_instance(node_instance, payload or {})

    return instance


@transaction.atomic
def advance_node_instance(node_instance: NodeInstance, payload: dict[str, Any] | None = None) -> None:
    workflow_instance = node_instance.workflow_instance
    workflow_node = node_instance.workflow_node
    context = build_context(workflow_instance=workflow_instance, node_instance=node_instance, payload=payload)

    if workflow_node.node_type == WorkflowNode.NODE_START:
        if workflow_node.assigned_role_id:
            workflow_instance.runtime_state["start_assigned_role_id"] = str(workflow_node.assigned_role_id)
            workflow_instance.save(update_fields=["runtime_state", "updated_at"])
        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        _release_waiting_nodes(workflow_instance)
        _advance_from_transitions(workflow_instance, workflow_node, context)
        return

    if workflow_node.node_type == WorkflowNode.NODE_TASK:
        task = _create_task_instance(node_instance=node_instance, role=workflow_node.assigned_role)
        node_instance.status = NodeInstance.STATUS_WAITING
        node_instance.save(update_fields=["status", "updated_at"])
        workflow_instance.current_node = workflow_node
        workflow_instance.current_assignee = task.assigned_user
        workflow_instance.current_state = workflow_node.name
        workflow_instance.save(update_fields=["current_node", "current_assignee", "current_state", "updated_at"])
        return

    if workflow_node.node_type == WorkflowNode.NODE_DECISION:
        transition = _select_next_transition(workflow_node, context)
        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        if transition:
            _start_target_node(workflow_instance, transition.target_node, context)
        return

    if workflow_node.node_type == WorkflowNode.NODE_PARALLEL_SPLIT:
        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        for transition in workflow_node.outgoing_transitions.select_related("target_node"):
            _start_target_node(workflow_instance, transition.target_node, context, branch_key=transition.external_id)
        return

    if workflow_node.node_type == WorkflowNode.NODE_PARALLEL_JOIN:
        if not _can_release_join(workflow_instance, workflow_node):
            node_instance.status = NodeInstance.STATUS_WAITING
            node_instance.save(update_fields=["status", "updated_at"])
            workflow_instance.current_node = workflow_node
            workflow_instance.current_state = workflow_node.name
            workflow_instance.save(update_fields=["current_node", "current_state", "updated_at"])
            return

        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        _advance_from_transitions(workflow_instance, workflow_node, context)
        return

    if workflow_node.node_type == WorkflowNode.NODE_MERGE:
        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        _advance_from_transitions(workflow_instance, workflow_node, context)
        return

    if workflow_node.node_type == WorkflowNode.NODE_END:
        node_instance.status = NodeInstance.STATUS_COMPLETED
        node_instance.completed_at = timezone.now()
        node_instance.save(update_fields=["status", "completed_at", "updated_at"])
        _record_node_completion(workflow_instance, workflow_node)
        workflow_instance.status = WorkflowInstance.STATUS_COMPLETED
        workflow_instance.current_node = workflow_node
        workflow_instance.current_state = workflow_node.name
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save(update_fields=["status", "current_node", "current_state", "completed_at", "updated_at"])
        return

    node_instance.status = NodeInstance.STATUS_COMPLETED
    node_instance.completed_at = timezone.now()
    node_instance.save(update_fields=["status", "completed_at", "updated_at"])
    _record_node_completion(workflow_instance, workflow_node)
    _advance_from_transitions(workflow_instance, workflow_node, context)


def _advance_from_transitions(workflow_instance: WorkflowInstance, workflow_node: WorkflowNode, context: dict[str, Any]) -> None:
    transition = _select_next_transition(workflow_node, context)
    if not transition:
        workflow_instance.status = WorkflowInstance.STATUS_COMPLETED
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save(update_fields=["status", "completed_at", "updated_at"])
        return

    _start_target_node(workflow_instance, transition.target_node, context)


def _start_target_node(workflow_instance: WorkflowInstance, target_node: WorkflowNode, context: dict[str, Any], branch_key: str = "") -> None:
    node_instance = _create_node_instance(workflow_instance=workflow_instance, workflow_node=target_node, branch_key=branch_key, context=context)
    workflow_instance.current_node = target_node
    workflow_instance.current_state = target_node.name
    workflow_instance.save(update_fields=["current_node", "current_state", "updated_at"])
    advance_node_instance(node_instance, context)


@transaction.atomic
def submit_task(task_instance: TaskInstance, *, action: str, comment: str = "", payload: dict[str, Any] | None = None, user: User | None = None) -> TaskInstance:
    if task_instance.status in {
        TaskInstance.STATUS_APPROVED,
        TaskInstance.STATUS_REJECTED,
        TaskInstance.STATUS_COMPLETED,
        TaskInstance.STATUS_CANCELLED,
    }:
        return task_instance

    refresh_task_sla(task_instance)

    merge_payload = _as_dict(payload)
    if action == "approve":
        merge_payload["approved"] = True
    elif action == "reject":
        merge_payload["approved"] = False

    _mark_task_completed(task_instance, action, comment, payload)

    workflow_instance = task_instance.workflow_instance
    workflow_instance.current_assignee = None
    workflow_instance.runtime_state["payload"] = {**_as_dict(workflow_instance.runtime_state.get("payload")), **merge_payload}
    workflow_instance.save(update_fields=["current_assignee", "runtime_state", "updated_at"])

    node_instance = task_instance.node_instance
    _record_node_completion(workflow_instance, node_instance.workflow_node)

    context = build_context(workflow_instance=workflow_instance, node_instance=node_instance, payload=payload)
    _advance_from_transitions(workflow_instance, node_instance.workflow_node, context)
    _release_waiting_nodes(workflow_instance)

    return task_instance


def ensure_role_assignment(user: User | None) -> list[str]:
    if not user:
        return []
    return list(user.workflow_roles.values_list("name", flat=True))