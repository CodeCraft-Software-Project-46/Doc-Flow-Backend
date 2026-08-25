from django.urls import path
from .views import *

urlpatterns = [

    # ================= OVERALL =================
    path("widgets/running-documents/", RunningDocumentsView.as_view()),      
    path("widgets/active-overdue-tasks/", ActiveOverdueTasksView.as_view()), #Class → becomes callable view function using .as_view()
    path("widgets/completed-tasks/", CompletedTasksView.as_view()),
    path("widgets/sla-compliance/", SLAComplianceView.as_view()),
    path("widgets/sla-distribution/", SLADistributionView.as_view()),
    path("widgets/bottleneck-workflows/", BottleneckWorkflowsView.as_view()),
    path("widgets/user-performance/", UserPerformanceView.as_view()),
    path("widgets/users/", UserListView.as_view()),
    path("widgets/my-performance/", MyPerformanceView.as_view()),

    # ================= CONFIG =================
    path("config/bottleneck-weights/", BottleneckWeightsConfigView.as_view()),

    # ================= WORKFLOW =================
    path("widgets/workflows/", WorkflowListView.as_view()),

    # KPI widgets
    path("widgets/workflow/<int:workflow_id>/running-instances/", WorkflowRunningInstancesView.as_view()),
    path("widgets/workflow/<int:workflow_id>/avg-completion-time/", WorkflowAvgCompletionTimeView.as_view()),
    path("widgets/workflow/<int:workflow_id>/sla-compliance/", WorkflowSLAComplianceView.as_view()),

    # flow + structure
    path("widgets/workflow/<int:workflow_id>/step-flow/", WorkflowStepFlowView.as_view()),

    # drilldown
    path("widgets/workflow/<int:workflow_id>/instances/", WorkflowInstanceListView.as_view()),
    path("widgets/instance/<int:instance_id>/drilldown/", InstanceDrilldownView.as_view()),
]