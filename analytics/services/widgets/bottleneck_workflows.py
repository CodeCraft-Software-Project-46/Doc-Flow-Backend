import math
from analytics.models import Workflow, TaskInstance, WorkflowInstance
from django.db.models import Avg, F, ExpressionWrapper, DurationField

def get_bottleneck_workflows():

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

    