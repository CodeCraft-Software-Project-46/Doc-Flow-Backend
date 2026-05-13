from django.db.models import Avg, F, ExpressionWrapper, DurationField
from analytics.models import Workflow, WorkflowInstance, TaskInstance, Document, User, Role
from django.utils import timezone

class WorkflowWidgets:

    # =====================================================
    # WHY: Frontend dropdown must only show meaningful workflows
    # i.e., workflows that actually have execution data
    # =====================================================
    @staticmethod
    def available_workflows():
        return Workflow.objects.filter(
            instances__isnull=False
        ).distinct().values("workflow_id", "name")

    # =====================================================
    # WHY: KPI must reflect ACTIVE context of selected workflow
    # =====================================================
    @staticmethod
    def total_instances(workflow_id):
        return WorkflowInstance.objects.filter(
            workflow_id=workflow_id,
            status="running"
        ).count()

    # =====================================================
    # WHY: completion time is only meaningful for completed instances
    # =====================================================
    @staticmethod
    def avg_completion_time(workflow_id):

        data = WorkflowInstance.objects.filter(
            workflow_id=workflow_id,
            status="completed"
        ).aggregate(
            avg_time=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
        )
        avg = data["avg_time"]
        return {
            "avg_completion_time_hours": round(avg.total_seconds() / 3600, 2) if avg else 0
        }

    # =====================================================
    # WHY: SLA must reflect completed workflow executions only
    # =====================================================
    @staticmethod
    def sla_compliance(workflow_id):

        tasks = TaskInstance.objects.filter(
            workflow_instance__workflow_id=workflow_id,
            workflow_instance__status="completed"
        )

        total = tasks.count()
        met = tasks.filter(sla_status="met").count()

        return {
            "total_tasks": total,
            "met_tasks": met,
            "percentage": round((met / total) * 100, 2) if total else 0
        }

    # =====================================================
    # WHY: Step flow is derived from TASK EXECUTION patterns
    # NOT static workflow definition only
    # =====================================================
    @staticmethod
    def step_flow(workflow_id):

        # All workflow instances
        instances = WorkflowInstance.objects.filter(
            workflow_id=workflow_id
        )
        total_instances = instances.count()
        completed_instances = instances.filter(
            status="completed"
        ).count()
        completion_rate = (
            round((completed_instances / total_instances) * 100, 2)
            if total_instances else 0
        )

        # Get all unique task names in order
        task_names = (
            TaskInstance.objects.filter(
                workflow_instance__workflow_id=workflow_id
            )
            .values_list("task_name", flat=True)
            .distinct()
        )

        steps = []

        for task_name in task_names:

            task_queryset = TaskInstance.objects.filter( #Get all tasks that belong to a specific workflow AND have a specific task name
                workflow_instance__workflow_id=workflow_id,
                task_name=task_name
            )

            received = task_queryset.count()

            passed = task_queryset.filter(
                status="completed"
            ).count()

            processing = task_queryset.filter(
                status="running" # or pending 
            ).count()

            breached = task_queryset.filter(
                sla_status="breached"
            ).count()

            sla_met = task_queryset.filter(
                sla_status="met"
            ).count()

            breach_percentage = (
                round((breached / received) * 100, 2)
                if received else 0
            )

            # Processing document names
            processing_documents = []

            running_tasks = task_queryset.filter( #From task_queryset, it picks only tasks that are: currently running (not completed yet) 
                status="running"
            ).select_related("workflow_instance")

            for task in running_tasks:
                document_id = task.workflow_instance.document_id
                if document_id:
                    try:
                        document = Document.objects.get( #If no document exists → Django throws error:
                            document_id=document_id
                        )
                        processing_documents.append(
                            document.document_name
                        )
                    except Document.DoesNotExist:
                        pass

            steps.append({
                "task_name": task_name,
                "received": received,
                "passed": passed,
                "processing": processing,
                "sla_met": sla_met,
                "breached": breached,
                "breach_percentage": breach_percentage,
                "processing_documents": processing_documents
            })

        return {
            "total_instances": total_instances,
            "completed_instances": completed_instances,
            "completion_rate": completion_rate,
            "steps": steps #oneda mewa 
        }

    # =====================================================
    # WHY: Instance dropdown needs enriched context
    # =====================================================
    @staticmethod
    def workflow_instances(workflow_id):

        instances = WorkflowInstance.objects.filter(
            workflow_id=workflow_id
        )

        return list(instances.values(
            "instance_id",
            "instance_name",
            "status",
            "created_at",
            "completed_at",
            "document_id"
        ))

    # =====================================================
    # WHY: Drilldown must show task-level execution clarity
    # =====================================================
    @staticmethod
    def instance_drilldown(instance_id):

        tasks = TaskInstance.objects.filter(
            workflow_instance_id=instance_id
        )

        result = []

        for t in tasks:

            user = User.objects.filter(role_id=t.assigned_role_id).first()
            role = Role.objects.filter(role_id=t.assigned_role_id).first()

            time_taken = None
            if t.completed_at:
                diff = t.completed_at - t.created_at
                time_taken = round(diff.total_seconds() / 3600, 2)

            result.append({
                "task_name": t.task_name,
                "assigned_user": user.user_name if user else None,
                "assigned_role": role.role_name if role else None,

                "status": t.status,
                "sla_status": t.sla_status,

                "sla_hours": t.sla_hours,
                "time_taken_hours": time_taken
            })

        return result