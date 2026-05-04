from django.utils import timezone
from django.apps import apps

def complete_workflow_if_done(workflow_instance_id):
    TaskInstance = apps.get_model("analytics", "TaskInstance")
    WorkflowInstance = apps.get_model("analytics", "WorkflowInstance")

    workflow = WorkflowInstance.objects.get(id=workflow_instance_id)

    tasks = TaskInstance.objects.filter(workflow_instance=workflow)

    # check if all tasks completed
    if all(t.status == "completed" for t in tasks):

        last_task = tasks.order_by("-completed_at").first()

        workflow.completed_at = last_task.completed_at
        workflow.status = "completed"
        workflow.save()

    return workflow