import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from analytics.services.widgets.overall_widgets import OverallWidgets

def run_and_print():
    out = {}
    try:
        out['running_documents'] = OverallWidgets.running_documents()
    except Exception as e:
        out['running_documents_error'] = str(e)

    try:
        overdue = OverallWidgets.active_overdue_tasks()
        out['active_overdue_tasks_count'] = overdue.get('count') if isinstance(overdue, dict) else str(overdue)
    except Exception as e:
        out['active_overdue_tasks_error'] = str(e)

    try:
        bottlenecks = OverallWidgets.bottleneck_workflows()
        out['bottleneck_workflows_count'] = len(bottlenecks) if isinstance(bottlenecks, list) else str(bottlenecks)
        out['bottleneck_workflows_sample'] = bottlenecks[:5] if isinstance(bottlenecks, list) else bottlenecks
    except Exception as e:
        out['bottleneck_workflows_error'] = str(e)

    print(json.dumps(out, default=str, indent=2))

if __name__ == '__main__':
    run_and_print()
