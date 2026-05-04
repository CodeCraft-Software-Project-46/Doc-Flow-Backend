from rest_framework.views import APIView
from rest_framework.response import Response

from analytics.services.widgets.running_documents import get_running_documents
from analytics.services.widgets.active_overdue_tasks import get_active_overdue_tasks
from analytics.services.widgets.completed_tasks import get_completed_tasks
from analytics.services.widgets.sla_compliance import get_sla_compliance
from analytics.services.widgets.sla_distribution import get_sla_distribution
from analytics.services.widgets.bottleneck_workflows import get_bottleneck_workflows
from analytics.services.widgets.user_performance import get_user_performance
from analytics.services.workflow_widgets import WorkflowWidgets


# =====================================================
# OVERALL WIDGETS (each is separate API)
# =====================================================

class RunningDocumentsView(APIView):
    def get(self, request):
        return Response({"value": get_running_documents()})

#Your class inherits from APIView which gives 
class ActiveOverdueTasksView(APIView):   #self means current object refernce      #this class inherits from APIView → becomes a view that can handle API requests
    def get(self, request): # when receive a GET request → run this function      #request means all the info about the incoming API request (headers, query params, body, meta data,loggedin user,etc.)
        return Response(get_active_overdue_tasks()) #Response will convert python dict to JSON response and send back to frontend by using Response() helper from DRF
        # return Response({"count": 5})                {
        #                                                "count": 5
        #                                             }

class CompletedTasksView(APIView):
    def get(self, request):
        return Response(get_completed_tasks())


class SLAComplianceView(APIView):
    def get(self, request):
        return Response(get_sla_compliance())


class SLADistributionView(APIView):
    def get(self, request):
        return Response(get_sla_distribution())


class BottleneckWorkflowsView(APIView):
    def get(self, request):
        return Response(get_bottleneck_workflows())


class UserPerformanceView(APIView):
    def get(self, request):
        return Response(get_user_performance())


# =====================================================
# WORKFLOW WIDGETS (ALL SEPARATE)
# =====================================================

class WorkflowTotalInstancesView(APIView):
    def get(self, request, workflow_id):
        return Response({"value": WorkflowWidgets.total_instances(workflow_id)})


class WorkflowCompletedInstancesView(APIView):
    def get(self, request, workflow_id):
        return Response({"value": WorkflowWidgets.completed_instances(workflow_id)})


class WorkflowAvgCompletionTimeView(APIView):
    def get(self, request, workflow_id):
        return Response(WorkflowWidgets.avg_completion_time(workflow_id))


class WorkflowSLAComplianceView(APIView):
    def get(self, request, workflow_id):
        return Response(WorkflowWidgets.sla_compliance(workflow_id))


class WorkflowStepFlowView(APIView):
    def get(self, request, workflow_id):
        return Response(WorkflowWidgets.step_flow(workflow_id))


class InstanceDrilldownView(APIView):
    def get(self, request, instance_id):
        
        return Response(WorkflowWidgets.instance_drilldown(instance_id))