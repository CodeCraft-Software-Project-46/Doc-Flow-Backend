from analytics.models import TaskInstance
def get_active_overdue_tasks():
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