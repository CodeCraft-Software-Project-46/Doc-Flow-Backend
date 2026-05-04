from analytics.models import TaskInstance, WorkflowInstance
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField


class WorkflowWidgets:

    # 🔹 Total Instances
    @staticmethod
    def total_instances(workflow_id):
        return WorkflowInstance.objects.filter(workflow_id=workflow_id).count()

    # 🔹 Completed Instances
    @staticmethod
    def completed_instances(workflow_id):
        return WorkflowInstance.objects.filter(
            workflow_id=workflow_id,
            status="completed"
        ).count()

    # 🔹 Avg Completion Time
    @staticmethod
    def avg_completion_time(workflow_id):
        return WorkflowInstance.objects.filter(
            workflow_id=workflow_id,
            status="completed"
        ).aggregate(
            avg_completion_time=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
        )

    # 🔹 SLA Compliance (Workflow)
    @staticmethod
    def sla_compliance(workflow_id):
        tasks = TaskInstance.objects.filter(
            workflow_instance__workflow_id=workflow_id,
            status="completed"
        )

        total = tasks.count()
        met = tasks.filter(sla_status="met").count()

        return {
            "total": total,
            "met": met,
            "percentage": (met / total * 100) if total else 0
        }

    # 🔹 Step Flow
    @staticmethod
    def step_flow(workflow_id):
        return TaskInstance.objects.filter(
            workflow_instance__workflow_id=workflow_id
        ).values("task_name").annotate(
            received=Count("task_id"),
            processing=Count("task_id", filter=Q(status="running")),
            passed=Count("task_id", filter=Q(status="completed")),
            sla_met=Count("task_id", filter=Q(sla_status="met"))
        )

    # 🔹 Instance Drilldown
    @staticmethod
    def instance_drilldown(instance_id):
        return TaskInstance.objects.filter(
            workflow_instance_id=instance_id
        ).values(
            "task_name",
            "assigned_role_id",
            "created_at",
            "completed_at",
            "sla_hours",
            "status",
            "sla_status"
        )