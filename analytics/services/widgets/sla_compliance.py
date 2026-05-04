from analytics.models import TaskInstance

def get_sla_compliance():
    completed = TaskInstance.objects.filter(status="completed")

    total = completed.count()
    met = completed.filter(sla_status="met").count()

    return {
        "total": total,
        "met": met,
        "percentage": round((met / total * 100), 2) if total else 0
    }