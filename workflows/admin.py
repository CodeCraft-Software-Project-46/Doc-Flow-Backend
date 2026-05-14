from django.contrib import admin

from .models import Department, NodeInstance, Notification, Role, TaskInstance, UserProfile, Workflow, WorkflowInstance, WorkflowNode, WorkflowTransition


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "description")
    list_filter = ("department",)
    search_fields = ("name", "department__name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "role__name")


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0
    fields = ("external_id", "node_type", "name", "position_x", "position_y", "assigned_role")


class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    extra = 0
    fields = ("external_id", "source_node", "target_node", "connection_type", "is_default", "priority")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "version", "trigger", "updated_at")
    list_filter = ("status", "trigger")
    search_fields = ("name", "description", "external_id")
    inlines = [WorkflowNodeInline, WorkflowTransitionInline]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ("workflow", "status", "current_state", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("workflow__name", "document_name")


@admin.register(NodeInstance)
class NodeInstanceAdmin(admin.ModelAdmin):
    list_display = ("workflow_instance", "workflow_node", "status", "started_at", "completed_at")
    list_filter = ("status",)


@admin.register(TaskInstance)
class TaskInstanceAdmin(admin.ModelAdmin):
    list_display = ("workflow_instance", "node_instance", "status", "assigned_user", "assigned_role", "completed_at")
    list_filter = ("status",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "title", "assigned_role", "assigned_user", "read", "created_at")
    list_filter = ("notification_type", "read", "assigned_role")
    search_fields = ("title", "message", "assigned_role__name", "assigned_user__username")