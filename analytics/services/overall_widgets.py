from unittest import result
import math
from analytics.models import Workflow,TaskInstance, WorkflowInstance, User
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone

class OverallWidgets:

    # 🔹 1. Running Documents
    @staticmethod
    def running_documents():
        return WorkflowInstance.objects.filter(status="running").count()

    # 🔹 1. Active Overdue Tasks
    @staticmethod #this func belong to class but doesn't need object reference (self) → can be called directly by class name without creating an object
    def active_overdue_tasks():
        queryset = TaskInstance.objects.filter( #ORM
            sla_status="breached"
        ).exclude(
            status="completed"
        )

        return {
            "count": queryset.count(),
            "tasks": list( #convert queryset provided by .values() to list of dicts for JSON response
                queryset.values( #dictionary format for JSON response
                    "task_id",
                    "task_name",
                    "status",
                    "due_at",
                    "workflow_instance_id",
                    "workflow_instance__workflow_id" #double underscore to access related workflow_id from workflow_instance foreign key
                )
            )
        }

    # 🔹 2. Completed Tasks (COUNT ONLY)
    @staticmethod
    def completed_tasks():
        return {
            "count": TaskInstance.objects.filter(status="completed").count()
        }

    # 🔹 3. SLA Compliance
    @staticmethod
    def sla_compliance():
        completed = TaskInstance.objects.filter(status="completed")

        total = completed.count()
        met = completed.filter(sla_status="met").count()

        return {
            "total": total,
            "met": met,
            "percentage": round((met / total * 100), 2) if total else 0
        }

    # 🔹 4. SLA Distribution (Pie Chart)
    @staticmethod
    def sla_distribution():
        completed = TaskInstance.objects.filter(status="completed")

        met = completed.filter(sla_status="met").count()
        breached = completed.filter(sla_status="breached").count()

        return {
            "data": [
                {"name": "met", "value": met},
                {"name": "breached", "value": breached}
            ]
        }

    # 🔹 6. Bottleneck Workflows

    @staticmethod
    def bottleneck_workflows():

        workflows = Workflow.objects.all()
        result = []

        for wf in workflows:

            # ✅ Completed instances only
            completed_instances = WorkflowInstance.objects.filter(
                workflow_id=wf.workflow_id,
                status="completed"
            )

            instance_count = completed_instances.count()

            # ✅ Avg completion time
            avg_time = completed_instances.aggregate(
                avg=Avg(
                    ExpressionWrapper(
                        F("completed_at") - F("created_at"),
                        output_field=DurationField()
                    )
                )
            )["avg"]

            avg_time_hours = (
                avg_time.total_seconds() / 3600
                if avg_time else 0
            )

            # ✅ Tasks from completed instances only
            tasks = TaskInstance.objects.filter(
                workflow_instance__workflow_id=wf.workflow_id,
                workflow_instance__status="completed",
                status="completed"
            )

            total_tasks = tasks.count()

            breached_tasks = tasks.filter(
                sla_status="breached"
            ).count()

            breach_percentage = (
                (breached_tasks / total_tasks) * 100
                if total_tasks else 0
            )

            ## =====================================================
# ⭐ NORMALIZED BOTTLENECK SCORE (UPDATED)
# =====================================================

            # prevent divide by zero
            max_time_hours = max(avg_time_hours, 1)

            norm_time = avg_time_hours / max_time_hours
            norm_breach = breach_percentage / 100
            norm_task_volume = math.log(total_tasks + 1)

            score = (
                (0.45 * norm_time) +
                (0.45 * norm_breach) +
                (0.10 * norm_task_volume)
            )

            # confidence adjustment (important)
            if instance_count < 2:
                score *= 0.5

            # =====================================================
        # FINAL APPEND (IMPORTANT)
        # =====================================================
            result.append({
                "workflow_id": wf.workflow_id,
                "workflow_name": wf.name,

                "avg_completion_time_hours": round(avg_time_hours, 2),
                "breach_percentage": round(breach_percentage, 2),
                "total_tasks": total_tasks,
                "completed_instances": instance_count,

                # ⭐ ADD HERE
                "bottleneck_score": round(score, 4)
            })

        # =====================================================
        # SORT AFTER LOOP (IMPORTANT FIX)
        # =====================================================
        result.sort(
            key=lambda x: x["bottleneck_score"],
            reverse=True
        )

        return result

    # 🔹 7. User Performance
    @staticmethod
    def user_performance():

        data = TaskInstance.objects.filter(
            status="completed"
        ).values("assigned_role_id").annotate(
            total_tasks=Count("task_id"),

            breached_tasks=Count(
                "task_id",
                filter=Q(sla_status="breached")
            ),

            met_tasks=Count(
                "task_id",
                filter=Q(sla_status="met")
            ),

            avg_time=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
        )

        result = []

        for item in data:

            role_id = item["assigned_role_id"]

            user = User.objects.filter(role_id=role_id).first()
            user_name = user.user_name if user else f"Role {role_id}"

            total_tasks = item["total_tasks"]
            breached = item["breached_tasks"]
            met = item["met_tasks"]

            # SLA compliance (IMPORTANT KPI)
            sla_compliance = (
                (met / total_tasks) * 100
                if total_tasks else 0
            )

            avg_time = item["avg_time"]

            avg_time_hours = (
                round(avg_time.total_seconds() / 3600, 2)
                if avg_time else 0
            )

            result.append({
                "user_name": user_name,
                "role_id": role_id,

                "total_tasks": total_tasks,
                "breached_tasks": breached,
                "met_tasks": met,

                "avg_completion_time_hours": avg_time_hours,
                "sla_compliance": round(sla_compliance, 2)
            })

        return result