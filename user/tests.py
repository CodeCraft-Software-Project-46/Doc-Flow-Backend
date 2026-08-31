from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from user.models import Department, Role, Permission, User


class UserModuleTests(TestCase):

    # setup test data------------------------------------------
    def setUp(self):
        self.client = APIClient()

        # Create Permission
        self.permission = Permission.objects.create(
            permission_name="CREATE_USER",
            permission_description="Can create users",
            category="USER"
        )

        # Create Department
        self.department = Department.objects.create(
            name="IT",
            description="IT Department"
        )

        # Create Role under Department
        self.role = Role.objects.create(
            name="Admin",
            description="System Admin",
            department=self.department
        )

        # Assign permission to role
        self.role.permissions.add(self.permission)

    # create tests------------------------------------------------

    # Create Department
    def test_create_department(self):
        data = {
            "name": "Finance",
            "description": "Finance Department"
        }

        response = self.client.post(
            reverse("save-department"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

    # Duplicate Department validation
    def test_duplicate_department(self):
        data = {
            "name": "IT",
            "description": "Duplicate Department"
        }

        response = self.client.post(
            reverse("save-department"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # Create Role
    def test_create_role(self):
        data = {
            "name": "Manager",
            "description": "Department Manager",
            "department": str(self.department.id),
            "permissions": ["CREATE_USER"]
        }

        response = self.client.post(
            reverse("save-role"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

    # Role without permissions
    def test_role_without_permissions(self):
        data = {
            "name": "Employee",
            "description": "Employee Role",
            "department": str(self.department.id),
            "permissions": []
        }

        response = self.client.post(
            reverse("save-role"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # Create User
    def test_create_user(self):
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "contact_number": "0771234567",
            "address": "Colombo",
            "role": str(self.role.id)
        }

        response = self.client.post(
            reverse("save-user"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

    # Duplicate Email check
    def test_duplicate_email(self):
        User.objects.create(
            username="temp1",
            name="Existing User",
            email="john@example.com",
            contact_number="0771111111",
            address="Kandy",
            role=self.role
        )

        data = {
            "name": "New User",
            "email": "john@example.com",
            "contact_number": "0772222222",
            "address": "Colombo",
            "role": str(self.role.id)
        }

        response = self.client.post(
            reverse("save-user"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # One user per role rule
    def test_only_one_user_per_role(self):
        User.objects.create(
            username="user1",
            name="First User",
            email="first@example.com",
            contact_number="0771111111",
            address="Colombo",
            role=self.role
        )

        data = {
            "name": "Second User",
            "email": "second@example.com",
            "contact_number": "0772222222",
            "address": "Galle",
            "role": str(self.role.id)
        }

        response = self.client.post(
            reverse("save-user"),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    # get tests-------------------------------------------------

    # Get all users
    def test_get_users(self):
        response = self.client.get(reverse("get-user"))
        self.assertEqual(response.status_code, 200)

    # Get departments
    def test_get_departments(self):
        response = self.client.get(reverse("get-all-departments"))
        self.assertEqual(response.status_code, 200)

    # Get roles
    def test_get_roles(self):
        response = self.client.get(reverse("get-roles"))
        self.assertEqual(response.status_code, 200)

    # Get permissions
    def test_get_permissions(self):
        response = self.client.get(reverse("get-permissions"))
        self.assertEqual(response.status_code, 200)

    # update tests-------------------

    # Update User
    def test_update_user(self):
        user = User.objects.create(
            username="u1",
            name="Old Name",
            email="old@example.com",
            contact_number="0771111111",
            address="Kandy",
            role=self.role
        )

        data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "contact_number": "0779999999",
            "address": "Colombo",
            "role": str(self.role.id)
        }

        response = self.client.put(
            reverse("update-user", kwargs={"pk": user.id}),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)

    # Update Role
    def test_update_role(self):
        data = {
            "name": "Updated Role",
            "description": "Updated Desc",
            "department": str(self.department.id),
            "permissions": ["CREATE_USER"]
        }

        response = self.client.put(
            reverse("update-role", kwargs={"pk": self.role.id}),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)

    # Update Department
    def test_update_department(self):
        data = {
            "name": "Updated Department",
            "description": "Updated Description"
        }

        response = self.client.put(
            reverse("update-department", kwargs={"pk": self.department.id}),
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 200)

    # delete test cases-------------------------------

    # Delete Role
    def test_delete_role(self):
        response = self.client.delete(
            reverse("delete-role", kwargs={"pk": self.role.id})
        )
        self.assertEqual(response.status_code, 200)

    # Delete Department with user -fail
    def test_delete_department_with_users(self):
        User.objects.create(
            username="john123",
            name="John",
            email="john@test.com",
            contact_number="0779999999",
            address="Colombo",
            role=self.role
        )

        response = self.client.delete(
            reverse("delete-department", kwargs={"pk": self.department.id})
        )

        self.assertEqual(response.status_code, 400)

    # Delete Department without user -pass
    def test_delete_department_without_users(self):
        response = self.client.delete(
            reverse("delete-department", kwargs={"pk": self.department.id})
        )

        self.assertEqual(response.status_code, 200)
