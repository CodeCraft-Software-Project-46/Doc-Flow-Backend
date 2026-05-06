from django.utils import timezone
from analytics.models import WorkflowInstance, Workflow, Document


def get_running_documents():

    now = timezone.now()

    running_instances = WorkflowInstance.objects.filter(
        status="running"
    )

    # 🔥 preload workflows & documents (avoid N+1)
    workflows = {
        w.workflow_id: w.name
        for w in Workflow.objects.all()
    }

    documents = {
        d.document_id: d.document_name
        for d in Document.objects.all()
    }

    result = []

    for inst in running_instances:

        workflow_name = workflows.get(inst.workflow_id, "Unknown Workflow")
        document_name = documents.get(inst.document_id, "Unknown Document")

        running_hours = (
            now - inst.created_at
        ).total_seconds() / 3600

        result.append({
            "instance_id": inst.instance_id,
            "instance_name": inst.instance_name,

            "workflow_id": inst.workflow_id,
            "workflow_name": workflow_name,

            "document_id": inst.document_id,
            "document_name": document_name,

            "status": inst.status,
            "created_at": inst.created_at,

            "running_hours": round(running_hours, 2),
        })

    return {
        "count": running_instances.count(),
        "documents": result
    }