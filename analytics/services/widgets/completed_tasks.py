from analytics.models import TaskInstance

def get_completed_tasks():
    return {
        "count": TaskInstance.objects.filter(status="completed").count()
    }