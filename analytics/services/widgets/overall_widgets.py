import math
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, DurationField
from analytics.models import TaskInstance, WorkflowInstance, Workflow, User, Role, Document, Department, BottleneckScoreWeights

class OverallWidgets:

# reused methods
    @staticmethod
    def completed_tasks(date_from=None, date_to=None):
        qs = TaskInstance.objects.filter(
            status="completed",
            completed_at__isnull=False
        )
        if date_from: #filter by completion date, not creation date, so the time range reflects when work actually finished
            qs = qs.filter(completed_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(completed_at__date__lte=date_to)
        return qs

    @staticmethod
    def completed_workflow_instances(date_from=None, date_to=None):
        qs = WorkflowInstance.objects.filter(
            status="completed",
            completed_at__isnull=False
        )
        if date_from:
            qs = qs.filter(completed_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(completed_at__date__lte=date_to)
        return qs
    
    # RUNNING DOCUMENTS
    @staticmethod
    def running_documents():

        workflows = {}
        for workflow in Workflow.objects.all(): #Create workflows Dictionary to get workflow name by id for results dictionary
            workflows[workflow.workflow_id] = workflow.name         #{
                                                                    #     1: "Leave Approval",
                                                                    #     2: "Invoice Workflow"
                                                                    # }
        documents = {}                       #Create documents Dictionary to get document name by id for results
        for document in Document.objects.all():
            documents[document.document_id] = document.document_name

        now = timezone.now()

        instances = WorkflowInstance.objects.filter(status="running")

        result = []

        for inst in instances:
            running_hours = 0
            if inst.created_at:
                running_hours = (now - inst.created_at).total_seconds() / 3600 #Get Running Hours

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

    # ACTIVE OVERDUE TASKS
    @staticmethod
    def active_overdue_tasks():

        now = timezone.now()
        queryset = TaskInstance.objects.filter( #Get all tasks that are overdue
            sla_status="breached"
        ).exclude(status="completed")

        workflows = {} #Create workflows Dictionary to get workflow name by id for results dictionary
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
            wf_instance = task.workflow_instance #Get workflow instance of this task to access workflow_id and document_id for results list
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
                "due_at": task.due_at,
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


    # COMPLETED TASKS
    @staticmethod
    def completed_tasks_count(date_from=None, date_to=None):
        return {
            "count": OverallWidgets.completed_tasks(date_from, date_to).count()
        }


    # SLA COMPLIANCE
    @staticmethod
    def sla_compliance(date_from=None, date_to=None):

        completed = OverallWidgets.completed_tasks(date_from, date_to)

        total = completed.count()
        met = completed.filter(sla_status="met").count()

        percentage = round((met / total * 100), 2) if total else 0

        return {
            "total": total,
            "met": met, #epa
            "percentage": percentage
        }

    # SLA DISTRIBUTION
    @staticmethod
    def sla_distribution(date_from=None, date_to=None):

        completed = OverallWidgets.completed_tasks(date_from, date_to)

        met = completed.filter(sla_status="met").count()
        breached = completed.filter(sla_status="breached").count()

        return [
            {"name": "met", "value": met},
            {"name": "breached", "value": breached}
        ]

    # BOTTLENECK WORKFLOWS
    @staticmethod
    def bottleneck_workflows(date_from=None, date_to=None):

        workflows = Workflow.objects.all() #Get all workflows
        metrics = [] #Create a empty list to store results

        for wf in workflows:

            instances = OverallWidgets.completed_workflow_instances(date_from, date_to).filter( #Get all completed instances of this workflow
                workflow_id=wf.workflow_id
            )
            instance_count = instances.count()

            avg_time = instances.aggregate( #Get average completion time for each workflow 
                avg=Avg(
                    ExpressionWrapper( #Calculate this AND treat result as a TIME duration 
                        F("completed_at") - F("created_at"),
                        output_field=DurationField() #time based calculation
                    )
                )
            )["avg"]

            avg_hours = (avg_time.total_seconds() / 3600) if avg_time else 0 #convert second to hours

            tasks = OverallWidgets.completed_tasks(date_from, date_to).filter( #Get all completed tasks of this workflow
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

        max_hours = max([m["avg_hours"] for m in metrics], default=1) or 1 #FIND MAX avg_hours FOR NORMALIZATION; guard against all-zero avg_hours (e.g. no instances completed in a narrow date range)
        time_weight, breach_weight, volume_weight = BottleneckScoreWeights.current().normalized() #configurable via admin / BottleneckScoreWeights, defaults to 0.45/0.45/0.10
        result = []
        for m in metrics:
            norm_time = m["avg_hours"] / max_hours #How slow is this workflow compared to slowest one If max_hours = 0 → division error
            norm_breach = m["breach_pct"] / 100
            norm_volume = math.log(m["total_tasks"] + 1)   #compresses big numbers. log(1) = 0, log(10) = 2.3, log(100) = 4.6, log(1000) = 6.9 etc. Prevents high volume workflows from dominating the score

            score = (time_weight * norm_time) + (breach_weight * norm_breach) + (volume_weight * norm_volume)

            if m["instances"] < 2: #if workflow has only1 `instance`, reduce confidence by 50% because no enough hostory
                score *= 0.5

            result.append({
                "workflow_id": m["workflow"].workflow_id,
                "workflow_name": m["workflow"].name,
                "avg_completion_time_hours": round(m["avg_hours"], 2),
                "breach_percentage": round(m["breach_pct"], 2),
                "total_tasks": m["total_tasks"],
                "completed_instances": m["instances"], #
                "bottleneck_score": round(score, 4)
            })

        return sorted(result, key=lambda x: x["bottleneck_score"], reverse=True) #worst1 to best0 score max to min 

    # AVAILABLE USERS (for the "My Performance" widget's user picker)
    @staticmethod
    def available_users():
        return list(User.objects.order_by("user_name").values("user_id", "user_name"))

    # MY PERFORMANCE — single user's task history + SLA trend + motivational message
    @staticmethod
    def my_performance(user_id, date_from=None, date_to=None):

        user = User.objects.filter(user_id=user_id).first()
        if not user:
            return None

        # Tasks are attributed by role (see user_performance/instance_drilldown above —
        # TaskInstance has no user FK, only assigned_role_id), so this reflects the
        # signed-in user's role, not a strictly personal assignment.
        tasks = OverallWidgets.completed_tasks(date_from, date_to).filter(
            assigned_role_id=user.role_id
        ).select_related("workflow_instance", "workflow_instance__workflow").order_by("completed_at")

        task_rows = []
        daily = {}  # date -> {"total": n, "breached": n}

        for t in tasks:
            wf_instance = t.workflow_instance
            workflow = wf_instance.workflow if wf_instance else None

            time_taken = None
            if t.completed_at:
                diff = t.completed_at - t.created_at
                time_taken = round(diff.total_seconds() / 3600, 2)

            task_rows.append({
                "task_name": t.task_name,
                "workflow_name": workflow.name if workflow else None,
                "instance_name": wf_instance.instance_name if wf_instance else None,
                "sla_hours": t.sla_hours,
                "time_taken_hours": time_taken,
                "sla_status": t.sla_status,
                "completed_at": t.completed_at,
            })

            if t.completed_at:
                day = t.completed_at.date().isoformat()
                bucket = daily.setdefault(day, {"total": 0, "breached": 0})
                bucket["total"] += 1
                if t.sla_status == "breached":
                    bucket["breached"] += 1

        total = len(task_rows)
        met = sum(1 for r in task_rows if r["sla_status"] == "met")
        breached = sum(1 for r in task_rows if r["sla_status"] == "breached")
        met_pct = round((met / total * 100), 2) if total else 0
        breach_pct = round((breached / total * 100), 2) if total else 0

        durations = [r["time_taken_hours"] for r in task_rows if r["time_taken_hours"] is not None]
        avg_time = round(sum(durations) / len(durations), 2) if durations else 0

        trend = [
            {
                "date": day,
                "total_tasks": bucket["total"],
                "breached_tasks": bucket["breached"],
                "breach_percentage": round(bucket["breached"] / bucket["total"] * 100, 2),
            }
            for day, bucket in sorted(daily.items())
        ]

        # Motivation: compare the breach rate across the first vs second half of the
        # days with activity in this range, so the widget can nudge the user toward
        # a downward trend rather than just showing a static snapshot.
        motivation = {
            "trend_direction": "insufficient_data",
            "first_half_avg": None,
            "second_half_avg": None,
            "delta": None,
        }

        if len(trend) >= 2:
            mid = len(trend) // 2
            first_half = trend[:mid]
            second_half = trend[mid:]

            first_avg = sum(d["breach_percentage"] for d in first_half) / len(first_half)
            second_avg = sum(d["breach_percentage"] for d in second_half) / len(second_half)
            delta = round(second_avg - first_avg, 2)

            if delta < -0.5:
                direction = "improving"
            elif delta > 0.5:
                direction = "worsening"
            else:
                direction = "stable"

            motivation = {
                "trend_direction": direction,
                "first_half_avg": round(first_avg, 2),
                "second_half_avg": round(second_avg, 2),
                "delta": delta,
            }

        return {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "summary": {
                "total_tasks": total,
                "met_tasks": met,
                "breached_tasks": breached,
                "met_percentage": met_pct,
                "breach_percentage": breach_pct,
                "avg_time_taken_hours": avg_time,
            },
            "tasks": task_rows,
            "trend": trend,
            "motivation": motivation,
        }

    # USER PERFORMANCE
    @staticmethod
    def user_performance(date_from=None, date_to=None):

        data = OverallWidgets.completed_tasks(date_from, date_to).values(
            "assigned_role_id" #completed tasks Group them by role (user role)
        ).annotate( #calculate metrics per role
            total_tasks=Count("task_id"), # total completed tasks assigned to this role
            breached_tasks=Count("task_id", filter=Q(sla_status="breached")),
            met_tasks=Count("task_id", filter=Q(sla_status="met")),
            avg_time=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
        )

        users = {u.role_id: u for u in User.objects.all()}#Create users Dictionary to get user details by role_id for results dictionary

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