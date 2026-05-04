from rest_framework.views import APIView
from rest_framework.response import Response

from analytics.services.overall_widgets import OverallWidgets
from analytics.services.workflow_widgets import WorkflowWidgets


# =====================================================
# OVERALL WIDGETS (each is separate API)
# =====================================================

class RunningDocumentsView(APIView):
    def get(self, request):
        return Response({"value": OverallWidgets.running_documents()}) 

#Your class inherits from APIView which gives 
class ActiveOverdueTasksView(APIView):   #self means current object refernce      #this class inherits from APIView → becomes a view that can handle API requests
    def get(self, request): # when receive a GET request → run this function      #request means all the info about the incoming API request (headers, query params, body, meta data,loggedin user,etc.)
        return Response(OverallWidgets.active_overdue_tasks()) #Response will convert python dict to JSON response and send back to frontend by using Response() helper from DRF
        # return Response({"count": 5})                {
        #                                                "count": 5
        #                                             }

class CompletedTasksView(APIView):
    def get(self, request):
        return Response(OverallWidgets.completed_tasks())


class SLAComplianceView(APIView):
    def get(self, request):
        return Response(OverallWidgets.sla_compliance())


class SLADistributionView(APIView):
    def get(self, request):
        return Response(OverallWidgets.sla_distribution())


class BottleneckWorkflowsView(APIView):
    def get(self, request):
        return Response(OverallWidgets.bottleneck_workflows())


class UserPerformanceView(APIView):
    def get(self, request):
        return Response(OverallWidgets.user_performance())


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