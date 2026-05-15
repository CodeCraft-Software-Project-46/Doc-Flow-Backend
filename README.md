# Doc-Flow-Backend

This repository contains the Django backend for Doc-Flow. Below are focused notes to help you contribute to specific subsystems: Working Hours configuration, the SLA engine, Analytics (overall and workflow widgets), and the Chatbot service.

## Contributing: Key Areas

- **Working Hours Config**: configuration and models live under [working_hours](working_hours). See [working_hours/models.py](working_hours/models.py) and [working_hours/serializers.py](working_hours/serializers.py) for the canonical data structures and API representation. To add or change work-hour logic, update models/serializers and corresponding tests in [working_hours/tests.py](working_hours/tests.py).

- **SLA Engine**: SLA scheduling and calculation logic is in [sla_engine](sla_engine). Important files:
	- [sla_engine/scheduler.py](sla_engine/scheduler.py) — manages periodic scheduling of SLA tasks.
	- [sla_engine/services/sla_calculator.py](sla_engine/services/sla_calculator.py) and [sla_engine/services/sla_service.py](sla_engine/services/sla_service.py) — core calculation and service helpers.
	- [sla_engine/management/commands/reschedule_sla_tasks.py](sla_engine/management/commands/reschedule_sla_tasks.py) — CLI entry to reschedule jobs.

	When contributing changes to SLA logic:
	- Add/adjust unit tests in [sla_engine/tests/test_sla_unit.py](sla_engine/tests/test_sla_unit.py).
	- If changing scheduling behavior, verify management commands and signal handlers in [sla_engine/signals.py](sla_engine/signals.py).

- **Analytics (Overall & Workflow Widgets)**: analytics endpoints and widget helpers are in [analytics](analytics). Notable locations:
	- API/views: [analytics/views.py](analytics/views.py) and [analytics/urls.py](analytics/urls.py)
	- Backend widget utilities: [analytics/services/widgets/overall_widgets.py](analytics/services/widgets/overall_widgets.py) and [analytics/services/widgets/workflow_widgets.py](analytics/services/widgets/workflow_widgets.py)

	To add a new chart or metric:
	- Implement data aggregation in the appropriate widget helper.
	- Expose a view for the frontend to call and add/update serializers/models as needed.
	- Add tests to [analytics/tests.py](analytics/tests.py).

- **Chatbot**: backend LLM integration and APIs are in [chatbot](chatbot):
	- [chatbot/llm_service.py](chatbot/llm_service.py) — LLM/LLM-provider integration.
	- [chatbot/prompt_service.py](chatbot/prompt_service.py) — prompt construction/helpers.
	- API views: [chatbot/views.py](chatbot/views.py) and [chatbot/urls.py](chatbot/urls.py).

	Contribution notes:
	- Keep secrets and API keys out of the repo; use environment variables.
	- Add tests to [chatbot/tests.py](chatbot/tests.py) when changing conversation handling.

## Workflow & Tests

- Run the Django test suite for quick verification:

```bash
python manage.py test
```

- When updating models or migrations, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Questions & PRs

When opening a PR for any of the areas above, include:
- A short description of the change and affected files.
- Test coverage for logic changes.
- Any migration steps or environment variables required to run the change locally.

Thanks for contributing — small, focused PRs are easiest to review.