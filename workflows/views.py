from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Department, Notification, Role, TaskInstance, UserProfile, Workflow, WorkflowInstance, WorkflowNode, WorkflowTransition
from .serializers import (
    DepartmentSerializer,
    NotificationSerializer,
    RoleSerializer,
    TaskInstanceSerializer,
    TaskSubmissionSerializer,
    UserProfileSerializer,
    WorkflowDefinitionWriteSerializer,
    WorkflowInstanceSerializer,
    WorkflowListSerializer,
    WorkflowNodeReadSerializer,
    WorkflowNodeWriteSerializer,
    WorkflowReadSerializer,
    WorkflowStartSerializer,
    WorkflowStatusSerializer,
    WorkflowTransitionReadSerializer,
    WorkflowTransitionWriteSerializer,
)
from .services import refresh_task_sla, save_workflow_definition, start_workflow_instance


UUID_REGEX = r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"detail": "CSRF cookie set"})


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.select_related("user", "role", "role__department").all().order_by("user__username")
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.select_related("department").all().prefetch_related("users")
    serializer_class = RoleSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get("department_id")
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset


class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Workflow.objects.all()
        if self.action == "list":
            return queryset.select_related("created_by").order_by("-updated_at")
        return queryset.select_related("created_by").prefetch_related("nodes", "transitions")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return WorkflowDefinitionWriteSerializer
        if self.action == "list":
            return WorkflowListSerializer
        return WorkflowReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        workflow = serializer.save()
        output = WorkflowReadSerializer(workflow, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop("partial", False), context={"request": request})
        serializer.is_valid(raise_exception=True)
        workflow = serializer.save()
        output = WorkflowReadSerializer(workflow, context={"request": request})
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        workflow = self.get_object()
        serializer = WorkflowStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = start_workflow_instance(
            workflow,
            started_by=request.user if request.user.is_authenticated else None,
            payload=serializer.validated_data.get("payload", {}),
            document_name=serializer.validated_data.get("documentName", ""),
            document_type=serializer.validated_data.get("documentType", ""),
        )
        return Response(WorkflowInstanceSerializer(instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="nodes")
    def add_node(self, request, pk=None):
        workflow = self.get_object()
        serializer = WorkflowNodeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        payload["nodes"] = [payload]
        workflow.definition = {**(workflow.definition or {}), "nodes": list((workflow.definition or {}).get("nodes", [])) + [request.data]}
        workflow.save(update_fields=["definition", "updated_at"])
        saved = save_workflow_definition({**workflow.definition, "workflowId": workflow.external_id}, created_by=request.user if request.user.is_authenticated else workflow.created_by)
        node = saved.nodes.get(external_id=payload.get("id") or request.data.get("id"))
        return Response(WorkflowNodeReadSerializer(node).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="transitions")
    def add_transition(self, request, pk=None):
        workflow = self.get_object()
        serializer = WorkflowTransitionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workflow.definition = {**(workflow.definition or {}), "connections": list((workflow.definition or {}).get("connections", [])) + [request.data]}
        workflow.save(update_fields=["definition", "updated_at"])
        saved = save_workflow_definition({**workflow.definition, "workflowId": workflow.external_id}, created_by=request.user if request.user.is_authenticated else workflow.created_by)
        transition = saved.transitions.get(external_id=serializer.validated_data.get("id") or request.data.get("id"))
        return Response(WorkflowTransitionReadSerializer(transition).data, status=status.HTTP_201_CREATED)


class WorkflowInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        WorkflowInstance.objects.all()
        .select_related("workflow", "current_assignee", "started_by")
        .prefetch_related(
            "node_instances__workflow_node",
            "node_instances__task_instance__assigned_role",
            "node_instances__task_instance__assigned_user",
        )
    )
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(id__regex=UUID_REGEX)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        instance = self.get_object()
        return Response(WorkflowStatusSerializer(instance).data)


class TaskInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskInstance.objects.all().select_related(
        "workflow_instance__workflow",
        "node_instance__workflow_node",
        "assigned_user",
        "assigned_role",
    )
    serializer_class = TaskInstanceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_id = self.request.query_params.get("role_id")
        if role_id:
            queryset = queryset.filter(assigned_role_id=role_id)

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value.upper())

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        tasks = list(queryset)
        for task in tasks:
            refresh_task_sla(task)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        task = self.get_object()
        payload = request.data.get("payload", {})
        if isinstance(payload, str):
            payload = {}

        uploaded_files = request.FILES.getlist("files") if hasattr(request, "FILES") else []
        if uploaded_files:
            existing_submission = task.submission_data if isinstance(task.submission_data, dict) else {}
            existing_files = existing_submission.get("files", []) if isinstance(existing_submission.get("files", []), list) else []
            payload = {
                **(payload if isinstance(payload, dict) else {}),
                "files": [*existing_files, *[f.name for f in uploaded_files]],
            }

        serializer = TaskSubmissionSerializer(
            data={
                "action": request.data.get("action") or "complete",
                "comment": request.data.get("comment", ""),
                "payload": payload if isinstance(payload, dict) else {},
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.update(task, serializer.validated_data)
        return Response(TaskInstanceSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        task = self.get_object()
        action_value = request.data.get("action") or "complete"
        serializer = TaskSubmissionSerializer(
            data={
                "action": action_value,
                "comment": request.data.get("comment", ""),
                "payload": request.data.get("payload", {}),
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.update(task, serializer.validated_data)
        return Response(TaskInstanceSerializer(task).data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.select_related("assigned_role", "task_instance", "workflow_instance").all()
    serializer_class = NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_id = self.request.query_params.get("role_id")
        if role_id:
            queryset = queryset.filter(assigned_role_id=role_id)
        return queryset

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["read", "read_at", "updated_at"])
        return Response(NotificationSerializer(notification).data)