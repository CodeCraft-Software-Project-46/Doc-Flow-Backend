from analytics.models import WorkflowInstance

def get_running_documents():
    return WorkflowInstance.objects.filter(status="running").count()