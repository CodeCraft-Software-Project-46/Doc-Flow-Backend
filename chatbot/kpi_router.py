"""Routes chatbot questions that ask for a known KPI/metric straight to the
same widget functions the analytics charts already use (analytics/services/
widgets/), instead of asking the LLM to hand-write aggregate SQL for numbers
that were never stored in the first place. Falls through to NL-to-SQL (or
RAG) when nothing matches."""

from analytics.models import Workflow
from analytics.services.widgets.overall_widgets import OverallWidgets
from analytics.services.widgets.workflow_widgets import WorkflowWidgets

# Keyword groups -> widget callable, for metrics scoped to a single workflow
# (only tried when the question names a workflow that exists).
_WORKFLOW_SCOPED_KEYWORDS = [
    (("completion time", "how long does", "how long do"), lambda wf_id: WorkflowWidgets.avg_completion_time(wf_id)),
    (("step flow", "step breakdown", "steps of", "workflow steps"), lambda wf_id: WorkflowWidgets.step_flow(wf_id)),
    (("running instances",), lambda wf_id: {"running_instances": WorkflowWidgets.running_instances(wf_id)}),
    (("sla compliance", "sla percentage"), lambda wf_id: WorkflowWidgets.sla_compliance(wf_id)),
]

# Keyword groups -> widget callable, for organisation-wide metrics.
_GLOBAL_KEYWORDS = [
    (("bottleneck",), lambda: OverallWidgets.bottleneck_workflows()),
    (("overdue",), lambda: OverallWidgets.active_overdue_tasks()),
    (("user performance", "performance by user", "top performer"), lambda: OverallWidgets.user_performance()),
    (("running document",), lambda: OverallWidgets.running_documents()),
    (("completed task",), lambda: OverallWidgets.completed_tasks_count()),
    (("sla distribution",), lambda: OverallWidgets.sla_distribution()),
    (("sla compliance", "sla percentage"), lambda: OverallWidgets.sla_compliance()),
]


def _resolve_workflow_id(question: str):
    """Best-effort: find a workflow whose name is mentioned in the question."""
    question_lower = question.lower()
    for workflow_id, name in Workflow.objects.values_list("workflow_id", "name"):
        if name and name.lower() in question_lower:
            return workflow_id
    return None


def route(question: str):
    """Return the widget's result if the question matches a known KPI keyword, else None."""
    question_lower = question.lower()

    workflow_id = _resolve_workflow_id(question)
    if workflow_id is not None:
        # A specific workflow was named: only try metrics that are actually
        # scoped to one workflow. Org-wide keywords like "completed task" or
        # "bottleneck" describe the whole system, not one workflow, so
        # falling through to them here would silently answer a
        # workflow-specific question with an unrelated global number
        # instead. If nothing workflow-scoped matches, fall through to
        # NL-to-SQL (which can write a properly filtered query) rather than
        # a global KPI.
        for keywords, func in _WORKFLOW_SCOPED_KEYWORDS:
            if any(keyword in question_lower for keyword in keywords):
                return func(workflow_id)
        return None

    for keywords, func in _GLOBAL_KEYWORDS:
        if any(keyword in question_lower for keyword in keywords):
            return func()

    return None
