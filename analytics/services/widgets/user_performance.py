from analytics.models import TaskInstance, User
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField

def get_user_performance():

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