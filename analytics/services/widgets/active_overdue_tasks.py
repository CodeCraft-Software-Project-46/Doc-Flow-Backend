from datetime import datetime
from django.utils import timezone

from analytics.models import (
    TaskInstance, WorkflowInstance, Workflow,
    User, Role, Document, Department
)

def get_active_overdue_tasks():

    queryset = TaskInstance.objects.filter(
        sla_status="breached"
    ).exclude(
        status="completed"
    )

    result = []

    now = timezone.now()  # 🔥 IMPORTANT: consistent timezone-safe current time

    for task in queryset:

        wf_instance = WorkflowInstance.objects.filter(
            instance_id=task.workflow_instance_id
        ).first()

        workflow = Workflow.objects.filter(
            workflow_id=wf_instance.workflow_id
        ).first() if wf_instance else None

        document = Document.objects.filter(
            document_id=wf_instance.document_id
        ).first() if wf_instance else None

        role = Role.objects.filter(
            role_id=task.assigned_role_id
        ).first()

        user = User.objects.filter(
            role_id=task.assigned_role_id
        ).first()

        department = Department.objects.filter(
            department_id=user.department_id
        ).first() if user else None

        # 🔥 OVERDUE CALCULATION
        overdue_hours = None
        overdue_days = None

        if task.due_at:
            diff = now - task.due_at
            overdue_hours = round(diff.total_seconds() / 3600, 2)
            overdue_days = round(diff.total_seconds() / 86400, 2)

        result.append({
            "task_id": task.task_id,
            "task_name": task.task_name,
            "status": task.status,
            "due_at": task.due_at,

            # workflow context
            "instance_name": wf_instance.instance_name if wf_instance else None,
            "workflow_name": workflow.name if workflow else None,

            # document context
            "document_name": document.document_name if document else None,

            # user & role context
            "user_name": user.user_name if user else None,
            "role": role.role_name if role else None,
            "department": department.department_name if department else None,

            # 🔥 NEW OVERDUE METRICS
            "overdue_hours": overdue_hours,
            "overdue_days": overdue_days,

            "assigned_role_id": task.assigned_role_id
        })

    return {
        "count": len(result),
        "tasks": result
    }