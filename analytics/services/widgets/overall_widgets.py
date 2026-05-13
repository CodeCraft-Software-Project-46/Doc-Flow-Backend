import math
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, DurationField
from analytics.models import TaskInstance, WorkflowInstance, Workflow, User, Role, Document, Department

class OverallWidgets:

    # =========================================================
    # reusable base query methods to reduce code duplication and ensure consistency
    # =========================================================
    @staticmethod
    def _completed_tasks():
        return TaskInstance.objects.filter(
            status="completed",
            completed_at__isnull=False
        )

    @staticmethod
    def _completed_workflow_instances():
        return WorkflowInstance.objects.filter(
            status="completed",
            completed_at__isnull=False
        )

    # =========================================================
    # RUNNING DOCUMENTS
    # =========================================================
    @staticmethod
    def running_documents():

        workflows = {}
        for workflow in Workflow.objects.all(): #creates dictionary entries
            workflows[workflow.workflow_id] = workflow.name         #{
                                                                    #     1: "Leave Approval",
                                                                    #     2: "Invoice Workflow"
                                                                    # }
        documents = {}
        for document in Document.objects.all():
            documents[document.document_id] = document.document_name

        now = timezone.now()

        instances = WorkflowInstance.objects.filter(status="running")

        result = []

        for inst in instances:
            running_hours = 0
            if inst.created_at:
                running_hours = (now - inst.created_at).total_seconds() / 3600

            result.append({
                "instance_id": inst.instance_id,
                "instance_name": inst.instance_name,
                "workflow_id": inst.workflow_id,
                "workflow_name": workflows.get(inst.workflow_id),
                "document_id": inst.document_id,
                "document_name": documents.get(inst.document_id),
                "status": inst.status,
                "created_at": inst.created_at,
                "running_hours": round(running_hours, 2)
            })

        return {
            "count": instances.count(),
            "documents": result
        }

    # =========================================================
    # ACTIVE OVERDUE TASKS
    # =========================================================
    @staticmethod
    def active_overdue_tasks():

        now = timezone.now()
        queryset = TaskInstance.objects.filter(
            sla_status="breached"
        ).exclude(status="completed")

        workflows = {}
        for workflow in Workflow.objects.all():
            workflows[workflow.workflow_id] = workflow.name

        documents = {}
        for document in Document.objects.all():
            documents[document.document_id] = document.document_name

        users = {}
        for user in User.objects.all():
            users[user.role_id] = user

        roles = {}
        for role in Role.objects.all():
            roles[role.role_id] = role.role_name

        departments = {}
        for department in Department.objects.all():
            departments[department.department_id] = department.department_name

        result = []

        for task in queryset:
            wf_instance = task.workflow_instance
            user = users.get(task.assigned_role_id)
            overdue_hours = None
            overdue_days = None

            if task.due_at: #if due at exists
                diff = now - task.due_at
                overdue_hours = round(diff.total_seconds() / 3600, 2)
                overdue_days = round(diff.total_seconds() / 86400, 2)

            result.append({
                "task_id": task.task_id,
                "task_name": task.task_name,
                "status": task.status,
                "due_at": task.due_at,# epaa
                "instance_name": wf_instance.instance_name,
                "workflow_name": workflows.get(wf_instance.workflow_id),
                "document_name": documents.get(wf_instance.document_id),
                "user_name": user.user_name if user else None,
                "role": roles.get(task.assigned_role_id),
                "department": departments.get(user.department_id) if user else None,
                "overdue_hours": overdue_hours,
                "overdue_days": overdue_days
            })

        return {
            "count": len(result),
            "tasks": result
        }

    # =========================================================
    # COMPLETED TASKS
    # =========================================================
    @staticmethod
    def completed_tasks():
        return {
            "count": OverallWidgets._completed_tasks().count()
        }

    # =========================================================
    # SLA COMPLIANCE (FIXED CONSISTENCY)
    # =========================================================
    @staticmethod
    def sla_compliance():

        completed = OverallWidgets._completed_tasks()

        total = completed.count()
        met = completed.filter(sla_status="met").count()

        percentage = round((met / total * 100), 2) if total else 0

        return {
            "total": total,
            "met": met, #epa 
            "percentage": percentage
        }

    # =========================================================
    # SLA DISTRIBUTION (FIXED CONSISTENCY)
    # =========================================================
    @staticmethod
    def sla_distribution():

        completed = OverallWidgets._completed_tasks()

        met = completed.filter(sla_status="met").count()
        breached = completed.filter(sla_status="breached").count()

        return {
            "data": [
                {"name": "met", "value": met},
                {"name": "breached", "value": breached}
            ]
        }

    # =========================================================
    # BOTTLENECK WORKFLOWS (CLEAN + CONSISTENT)
    # =========================================================
    @staticmethod
    def bottleneck_workflows():

        workflows = Workflow.objects.all()
        metrics = []

        for wf in workflows:
            instances = OverallWidgets._completed_workflow_instances().filter( #Get all completed instances of this workflow
                workflow_id=wf.workflow_id
            )
            instance_count = instances.count()

            avg_time = instances.aggregate( #Get average completion time for each workflow 
                avg=Avg(
                    ExpressionWrapper( #Calculate this AND treat result as a TIME duration 
                        F("completed_at") - F("created_at"),
                        output_field=DurationField() #time basedc calculation
                    )
                )
            )["avg"]

            avg_hours = (avg_time.total_seconds() / 3600) if avg_time else 0 #convert second to hours

            tasks = OverallWidgets._completed_tasks().filter( #Get all completed tasks of this workflow
                workflow_instance__workflow_id=wf.workflow_id #Task → WorkflowInstance → Workflow go through relationship to filter by workflow_id
            )

            total_tasks = tasks.count()
            breached = tasks.filter(sla_status="breached").count()

            breach_pct = (breached / total_tasks * 100) if total_tasks else 0

            metrics.append({
                "workflow": wf,
                "avg_hours": avg_hours,
                "breach_pct": breach_pct,
                "total_tasks": total_tasks,
                "instances": instance_count
            })

        max_hours = max([m["avg_hours"] for m in metrics], default=1) #FIND MAX avg_hours FOR NORMALIZATION 
        result = []
        for m in metrics:
            norm_time = m["avg_hours"] / max_hours #How slow is this workflow compared to slowest one If max_hours = 0 → division error
            norm_breach = m["breach_pct"] / 100
            norm_volume = math.log(m["total_tasks"] + 1)   #compresses big numbers. log(1) = 0, log(10) = 2.3, log(100) = 4.6, log(1000) = 6.9 etc. Prevents high volume workflows from dominating the score

            score = (0.45 * norm_time) + (0.45 * norm_breach) + (0.10 * norm_volume) #Hard-coded weights later we can move to settings

            if m["instances"] < 2: #if workflow has only1 `instance`, reduce confidence by 50% because no enough hostory
                score *= 0.5

            result.append({
                "workflow_id": m["workflow"].workflow_id,
                "workflow_name": m["workflow"].name,
                "avg_completion_time_hours": round(m["avg_hours"], 2),
                "breach_percentage": round(m["breach_pct"], 2),
                "total_tasks": m["total_tasks"],
                "completed_instances": m["instances"], #epa
                "bottleneck_score": round(score, 4)
            })

        return sorted(result, key=lambda x: x["bottleneck_score"], reverse=True) #worst1 to best0 score max to min 

    # =========================================================
    # USER PERFORMANCE (FIXED CONSISTENCY)
    # =========================================================
    @staticmethod
    def user_performance():

        data = OverallWidgets._completed_tasks().values(
            "assigned_role_id" #completed tasks by  Group them by role (user role)
        ).annotate(
            total_tasks=Count("task_id"),
            breached_tasks=Count("task_id", filter=Q(sla_status="breached")),
            met_tasks=Count("task_id", filter=Q(sla_status="met")),
            avg_time=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
        )

        users = {u.role_id: u for u in User.objects.all()}

        result = []

        for item in data:
            role_id = item["assigned_role_id"]
            user = users.get(role_id) #find which user belongs to this role

            total = item["total_tasks"]
            met = item["met_tasks"]

            compliance = (met / total * 100) if total else 0 #How many tasks were completed successfully 
            avg_hours = (item["avg_time"].total_seconds() / 3600) if item["avg_time"] else 0

            result.append({
                "user_name": user.user_name if user else f"Role {role_id}",
                "role_id": role_id,
                "total_tasks": total,
                "breached_tasks": item["breached_tasks"],
                "avg_completion_time_hours": round(avg_hours, 2),
                "sla_compliance": round(compliance, 2)
            })

        return sorted(result, key=lambda x: x["sla_compliance"], reverse=True) # best performer on top