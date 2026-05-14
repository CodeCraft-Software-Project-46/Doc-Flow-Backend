import uuid
# Create your tests here.

from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from user.models import Role, Department, Permission
from dashboard.models import Dashboard, Widget, WidgetPermission


class DashboardTests(TestCase):

    # setup
    def setUp(self):
        self.client = APIClient()


        # Create Department

        self.department = Department.objects.create(
            name="IT",
            description="IT Dept"
        )


        # Create Role

        self.role = Role.objects.create(
            name="Admin",
            description="System Admin",
            department=self.department
        )


        # Permission

        self.permission = Permission.objects.create(
            permission_name="VIEW_DASHBOARD",
            permission_description="View dashboards",
            category="DASHBOARD"
        )


        # Widget

        self.widget = Widget.objects.create(
            widget_code="W001",
            name="User Stats",
            category="STATS",
            min_width=2,
            max_width=6,
            min_height=2,
            max_height=6
        )

        # Link widget to permission
        WidgetPermission.objects.create(
            widget=self.widget,
            permission=self.permission
        )

    #get accessible widgets
    def test_get_accessible_widgets(self):
        response = self.client.get(
            reverse("getAccessibleWidgets", kwargs={"role_id": self.role.id})
        )

        self.assertEqual(response.status_code, 200)

    def test_get_accessible_widgets_invalid_role(self):
        fake_uuid = uuid.uuid4()  # valid UUID but not in DB

        response = self.client.get(
            reverse("getAccessibleWidgets", kwargs={"role_id": fake_uuid})
        )

        self.assertEqual(response.status_code, 404)

    # create-dashboard
    def test_create_dashboard(self):

        data = {
            "name": "Main Dashboard",
            "description": "Test dashboard",
            "role_id": str(self.role.id),
            "widgets": [
                {
                    "widget_code": "W001",
                    "pos_x": 0,
                    "pos_y": 0,
                    "width": 4,
                    "height": 3
                }
            ]
        }

        response = self.client.post(
            reverse("saveDashboard"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("dashboard_id", response.data)

    # get-all-dashboard
    def test_get_dashboard_list(self):

        Dashboard.objects.create(
            name="Dash 1",
            description="Test",
            role=self.role,
            status="active"
        )

        response = self.client.get(reverse("getAllDashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))

    # get dashboard
    def test_get_dashboard(self):

        dashboard = Dashboard.objects.create(
            name="Dash 2",
            description="Test",
            role=self.role,
            status="active"
        )

        response = self.client.get(
            reverse("getDashboard", kwargs={"dashboard_id": dashboard.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], dashboard.id)

    #update dashboard
    def test_update_dashboard(self):

        dashboard = Dashboard.objects.create(
            name="Old Dash",
            description="Old",
            role=self.role,
            status="draft"
        )

        data = {
            "name": "Updated Dash",
            "description": "Updated",
            "role_id": str(self.role.id),
            "status": "active",
            "widgets": []
        }

        response = self.client.put(
            reverse("updateDashboard", kwargs={"id": dashboard.id}),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)

    #change status
    def test_change_dashboard_status(self):

        dashboard = Dashboard.objects.create(
            name="Status Dash",
            description="Test",
            role=self.role,
            status="draft"
        )

        data = {"status": "active"}

        response = self.client.put(
            reverse("changeDashboardStatus", kwargs={"dashboard_id": dashboard.id}),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)

    # get active dashboard
    def test_get_active_dashboard(self):

        dashboard = Dashboard.objects.create(
            name="Active Dash",
            description="Test",
            role=self.role,
            status="active"
        )

        response = self.client.get(
            reverse("getActiveDashboard", kwargs={"role_id": self.role.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], dashboard.id)

    def test_get_active_dashboard_not_found(self):

        response = self.client.get(
            reverse("getActiveDashboard", kwargs={"role_id": self.role.id})
        )

        self.assertEqual(response.status_code, 404)

    #delete dashboard
    def test_delete_dashboard(self):

        dashboard = Dashboard.objects.create(
            name="Delete Dash",
            description="Test",
            role=self.role,
            status="draft"
        )

        response = self.client.delete(
            reverse("deleteDashboard", kwargs={"dashboard_id": dashboard.id})
        )

        self.assertEqual(response.status_code, 200)