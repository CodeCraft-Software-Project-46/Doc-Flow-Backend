from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from analytics.services.widgets.overall_widgets import OverallWidgets
from analytics.services.widgets.workflow_widgets import WorkflowWidgets
from analytics.models import BottleneckScoreWeights, TaskInstance, WorkflowInstance
from analytics.serializers import BottleneckScoreWeightsSerializer, CreateTaskSerializer


def parse_date_range(request):
    #reads the "from"/"to" query params (YYYY-MM-DD) shared by the overall analytics time-range filter
    date_from = parse_date(request.query_params.get("from") or "")
    date_to = parse_date(request.query_params.get("to") or "")
    return date_from, date_to

# OVERALL WIDGETS

class RunningDocumentsView(APIView):
    def get(self, request):
        return Response(OverallWidgets.running_documents())

#class inherits from APIView which gives you access to the get() method 
class ActiveOverdueTasksView(APIView):   #self means current object refernce      #this class inherits from APIView → becomes a view that can handle API requests
    def get(self, request): # when receive a GET request → run this function      #request means all the info about the incoming API request (headers, query params, body, meta data,loggedin user,etc.)
        return Response(OverallWidgets.active_overdue_tasks()) #Response will convert python dict to JSON response and send back to frontend by using Response() helper from DRF
        # return Response({"count": 5})                {
        #                                                "count": 5
        #                                             }

class CompletedTasksView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.completed_tasks_count(date_from, date_to))

class SLAComplianceView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.sla_compliance(date_from, date_to))


class SLADistributionView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.sla_distribution(date_from, date_to))


class BottleneckWorkflowsView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.bottleneck_workflows(date_from, date_to))


class UserPerformanceView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.user_performance(date_from, date_to))


class UserListView(APIView):
    def get(self, request):
        return Response(OverallWidgets.available_users())


class MyPerformanceView(APIView):
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        date_from, date_to = parse_date_range(request)
        result = OverallWidgets.my_performance(user_id, date_from, date_to)

        if result is None:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(result)


class RolePermissionsView(APIView):
    def get(self, request):
        return Response(OverallWidgets.role_permissions())


class TaskInstancesListView(APIView):
    def get(self, request):
        date_from, date_to = parse_date_range(request)
        return Response(OverallWidgets.task_instances(date_from, date_to))


# CONFIG

class BottleneckWeightsConfigView(APIView):
    """Read/update the weights (time/breach/volume) blended into bottleneck_score, instead of the old hard-coded 0.45/0.45/0.10 split."""

    def get(self, request):
        config = BottleneckScoreWeights.objects.order_by("-updated_at").first()

        if not config:
            return Response({"exists": False, "data": None})

        return Response({
            "exists": True,
            "data": BottleneckScoreWeightsSerializer(config).data
        })

    def post(self, request):
        # select_for_update + atomic: mirrors working_hours.save_config so two
        # concurrent first-time saves can't each create their own row.
        with transaction.atomic():
            config = (
                BottleneckScoreWeights.objects
                .select_for_update()
                .order_by("-updated_at")
                .first()
            )

            if config:
                serializer = BottleneckScoreWeightsSerializer(config, data=request.data, partial=True)
            else:
                serializer = BottleneckScoreWeightsSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Bottleneck score weights saved successfully",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {
                    "message": "Validation failed",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

# WORKFLOW WIDGETS

class WorkflowListView(APIView):
    def get(self, request):
        return Response(WorkflowWidgets.available_workflows())

class WorkflowRunningInstancesView(APIView):
    def get(self, request, workflow_id):
        return Response({
            "value": WorkflowWidgets.running_instances(workflow_id)
        })

class WorkflowAvgCompletionTimeView(APIView):
    def get(self, request, workflow_id):
        return Response(
            WorkflowWidgets.avg_completion_time(workflow_id)
        )

class WorkflowSLAComplianceView(APIView):
    def get(self, request, workflow_id):
        return Response(
            WorkflowWidgets.sla_compliance(workflow_id)
        )
    
#workflow step flow data

class WorkflowStepFlowView(APIView):
    def get(self, request, workflow_id):
        return Response(
            WorkflowWidgets.step_flow(workflow_id)
        )
    
#workflow instances drilldown

class WorkflowInstanceListView(APIView):
    def get(self, request, workflow_id):
        return Response(
            WorkflowWidgets.workflow_instances(workflow_id)
        )

class InstanceDrilldownView(APIView):
    def get(self, request, instance_id):
        return Response(
            WorkflowWidgets.instance_drilldown(instance_id)
        )


# TASKS (manual/testing)

class CreateTaskView(APIView):
    """
    Backs the "New Task" floating button on the analytics dashboard —
    lets you spin up a TaskInstance by hand (task name + SLA hours) to watch
    the SLA engine compute due_at and evaluate it, without writing SQL.

    created_at is always the server's current time, never taken from the
    request: this backend only ever runs in Sri Lanka (see
    sla.services.sla_calculator.PROJECT_TIME_ZONE), so "now" here already is
    the creator's local time.
    """

    def post(self, request):
        serializer = CreateTaskSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # New tasks are attached to the most recently created workflow
        # instance rather than requiring the button to also ask "which
        # instance?" — this endpoint is for quickly exercising the SLA
        # engine, not for modeling a real workflow run.
        workflow_instance = (
            WorkflowInstance.objects
            .order_by("-instance_id")
            .first()
        )

        if workflow_instance is None:
            return Response(
                {"detail": "No workflow instance exists to attach a task to."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = TaskInstance.objects.create(
            workflow_instance_id=workflow_instance.instance_id,
            task_name=serializer.validated_data["task_name"],
            created_at=timezone.now(),
            status="pending",
            sla_hours=serializer.validated_data["sla_hours"],
            assigned_role_id=2,
        )

        # The post_save signal (sla.signals.initialize_task_sla) computes and
        # saves due_at synchronously, but it does so on its own separately
        # fetched row, not this in-memory `task` object — without this
        # refresh, due_at below would still read back as the None it was
        # before the signal ran.
        task.refresh_from_db()

        return Response(
            {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "workflow_instance_id": task.workflow_instance_id,
                "created_at": task.created_at,
                "due_at": task.due_at,
                "sla_hours": task.sla_hours,
            },
            status=status.HTTP_201_CREATED,
        )


def _serialize_task_for_tester(task):
    return {
        "task_id": task.task_id,
        "task_name": task.task_name,
        "status": task.status,
        "created_at": task.created_at,
        "due_at": task.due_at,
        "sla_status": task.sla_status,
    }


class PendingTasksView(APIView):
    """
    Recent not-yet-completed tasks, for the "Open Tasks" list in the
    analytics dashboard's task tester panel — so a task created there (or by
    hand) can be marked completed from the UI instead of an UPDATE query.
    """

    def get(self, request):
        tasks = (
            TaskInstance.objects
            .filter(completed_at__isnull=True)
            .order_by("-created_at")[:20]
        )

        return Response(
            [_serialize_task_for_tester(t) for t in tasks]
        )


class CompleteTaskView(APIView):
    """
    Marks a task completed right now. Like CreateTaskView, completed_at is
    always the server's current time, never taken from the request — this
    backend only ever runs in Sri Lanka, so "now" here already is the local
    time the click happened.

    This only records completion; it does not evaluate sla_status itself —
    that still happens when the SLA engine's scheduled check reaches this
    task's due_at (or the reconcile safety net catches it), same as for any
    other task.
    """

    def post(self, request, task_id):
        try:
            task = TaskInstance.objects.get(task_id=task_id)
        except TaskInstance.DoesNotExist:
            return Response(
                {"detail": "Task not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if task.completed_at is not None:
            return Response(
                {"detail": "Task is already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.completed_at = timezone.now()
        task.status = "completed"
        task.save(update_fields=["completed_at", "status"])

        return Response(_serialize_task_for_tester(task))