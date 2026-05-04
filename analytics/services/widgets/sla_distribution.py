from analytics.models import TaskInstance

def get_sla_distribution():
    completed = TaskInstance.objects.filter(status="completed")

    met = completed.filter(sla_status="met").count()
    breached = completed.filter(sla_status="breached").count()

    return {
        "data": [
            {"name": "met", "value": met},
            {"name": "breached", "value": breached}
        ]
    }