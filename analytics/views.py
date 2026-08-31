from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from analytics.services.widgets.overall_widgets import OverallWidgets
from analytics.services.widgets.workflow_widgets import WorkflowWidgets
from analytics.models import BottleneckScoreWeights
from analytics.serializers import BottleneckScoreWeightsSerializer


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