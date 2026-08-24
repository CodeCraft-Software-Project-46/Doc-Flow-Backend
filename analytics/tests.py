"""HTTP contract tests for analytics dashboard widgets.

The analytics models are unmanaged because they point at reporting tables. These
tests mock the widget service layer and verify each public endpoint's contract.
"""

from datetime import date
from unittest.mock import patch

from django.apps import apps
from django.test import SimpleTestCase


class AnalyticsModuleSmokeTests(SimpleTestCase):
    def test_analytics_app_is_registered(self):
        self.assertTrue(apps.is_installed("analytics"))


class OverallWidgetApiTests(SimpleTestCase):
    """Test cases 7.x.4.1 through 7.x.4.7."""

    # Whether the view passes the parsed (date_from, date_to) query params
    # through to the widget method, or calls it with no arguments -- see
    # analytics/views.py's parse_date_range() usage per view.
    overall_cases = (
        ("sla_compliance", "/api/analytics/widgets/sla-compliance/", {"total": 10, "met": 8, "percentage": 80.0}, True),
        ("sla_distribution", "/api/analytics/widgets/sla-distribution/", [{"name": "met", "value": 8}, {"name": "breached", "value": 2}], True),
        ("running_documents", "/api/analytics/widgets/running-documents/", {"count": 1, "documents": [{"instance_id": 12, "status": "running"}]}, False),
        ("active_overdue_tasks", "/api/analytics/widgets/active-overdue-tasks/", {"count": 1, "tasks": [{"task_id": 22, "status": "running", "overdue_hours": 4.0}]}, False),
        ("completed_tasks_count", "/api/analytics/widgets/completed-tasks/", {"count": 9}, True),
        ("bottleneck_workflows", "/api/analytics/widgets/bottleneck-workflows/", [{"workflow_id": 3, "workflow_name": "Approval", "bottleneck_score": 0.85}], True),
        ("user_performance", "/api/analytics/widgets/user-performance/", [{"role_id": 5, "user_name": "Asha", "sla_compliance": 95.0}], True),
    )

    def test_overall_widget_endpoints_return_the_widget_payload(self):
        for method_name, url, expected_payload, takes_date_range in self.overall_cases:
            with self.subTest(widget=method_name):
                with patch(
                    f"analytics.views.OverallWidgets.{method_name}",
                    return_value=expected_payload,
                ) as widget_method:
                    response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), expected_payload)
                if takes_date_range:
                    widget_method.assert_called_once_with(None, None)
                else:
                    widget_method.assert_called_once_with()

    def test_date_range_query_params_are_parsed_and_forwarded_to_widgets(self):
        """A chart filtered to a date range (?from=&to=) must reach the widget
        layer as parsed date objects, not raw query strings."""
        for method_name, url, expected_payload, takes_date_range in self.overall_cases:
            if not takes_date_range:
                continue

            with self.subTest(widget=method_name), patch(
                f"analytics.views.OverallWidgets.{method_name}",
                return_value=expected_payload,
            ) as widget_method:
                response = self.client.get(url, {"from": "2024-01-01", "to": "2024-01-31"})

            self.assertEqual(response.status_code, 200)
            widget_method.assert_called_once_with(date(2024, 1, 1), date(2024, 1, 31))

    def test_invalid_date_query_params_are_treated_as_no_filter(self):
        with patch(
            "analytics.views.OverallWidgets.sla_compliance",
            return_value={"total": 0, "met": 0, "percentage": 0},
        ) as widget_method:
            response = self.client.get(
                "/api/analytics/widgets/sla-compliance/", {"from": "not-a-date", "to": ""}
            )

        self.assertEqual(response.status_code, 200)
        widget_method.assert_called_once_with(None, None)


class WorkflowWidgetApiTests(SimpleTestCase):
    """Test cases 7.x.4.8 through 7.x.4.13."""

    def test_running_instances_returns_the_workflow_count(self):
        with patch("analytics.views.WorkflowWidgets.running_instances", return_value=4) as widget_method:
            response = self.client.get("/api/analytics/widgets/workflow/7/running-instances/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"value": 4})
        widget_method.assert_called_once_with(7)

    def test_average_completion_time_returns_the_workflow_metric(self):
        expected_payload = {"avg_completion_time_hours": 12.5}
        with patch("analytics.views.WorkflowWidgets.avg_completion_time", return_value=expected_payload) as widget_method:
            response = self.client.get("/api/analytics/widgets/workflow/7/avg-completion-time/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_payload)
        widget_method.assert_called_once_with(7)

    def test_sla_compliance_returns_the_workflow_metric(self):
        expected_payload = {"total_tasks": 10, "met_tasks": 9, "percentage": 90.0}
        with patch("analytics.views.WorkflowWidgets.sla_compliance", return_value=expected_payload) as widget_method:
            response = self.client.get("/api/analytics/widgets/workflow/7/sla-compliance/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_payload)
        widget_method.assert_called_once_with(7)

    def test_step_flow_returns_the_workflow_structure(self):
        expected_payload = {"total_instances": 4, "completed_instances": 3, "completion_rate": 75.0, "steps": [{"task_name": "Review", "received": 4}]}
        with patch("analytics.views.WorkflowWidgets.step_flow", return_value=expected_payload) as widget_method:
            response = self.client.get("/api/analytics/widgets/workflow/7/step-flow/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_payload)
        widget_method.assert_called_once_with(7)

    def test_instances_returns_the_selected_workflow_instances(self):
        expected_payload = [{"instance_id": 101, "instance_name": "Invoice 101", "status": "running"}]
        with patch("analytics.views.WorkflowWidgets.workflow_instances", return_value=expected_payload) as widget_method:
            response = self.client.get("/api/analytics/widgets/workflow/7/instances/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_payload)
        widget_method.assert_called_once_with(7)

    def test_drilldown_returns_the_selected_instance_details(self):
        expected_payload = [{"task_name": "Review", "assigned_user": "Asha", "status": "completed", "time_taken_hours": 2.5}]
        with patch("analytics.views.WorkflowWidgets.instance_drilldown", return_value=expected_payload) as widget_method:
            response = self.client.get("/api/analytics/widgets/instance/101/drilldown/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_payload)
        widget_method.assert_called_once_with(101)
