from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from accounts.models import UserData, RoleData, PermissionData, UserRolePermissionData
from django.db import connection

class NotificationSystemTests(APITestCase):
    
    @classmethod
    def setUpClass(cls):
        """Bypass migrations and manually build the unmanaged tables in the test DB"""
        # 1. Temporarily tell Django we control these tables
        PermissionData._meta.managed = True
        RoleData._meta.managed = True
        UserData._meta.managed = True
        UserRolePermissionData._meta.managed = True
        
        # 2. Manually inject the tables into the database
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(PermissionData)
            schema_editor.create_model(RoleData)
            schema_editor.create_model(UserData)
            schema_editor.create_model(UserRolePermissionData)
            
        super().setUpClass()

    def setUp(self):
        """Runs before EVERY test method below"""
        self.perm, _ = PermissionData.objects.get_or_create(
            permission_id=24, 
            defaults={'permission_name': 'can_manage_notifications'}
        )
        
        self.role, _ = RoleData.objects.get_or_create(
            id='role_uuid_123', 
            defaults={'name': 'Marketing Manager'}
        )
        
        self.user_role_perm, _ = UserRolePermissionData.objects.get_or_create(
            role=self.role, 
            permission=self.perm
        )
        
        self.user = User.objects.create_user(username='Nesandu', password='password123')
        self.shadow_user = UserData.objects.create(
            username='Nesandu',
            role=self.role,
            email='nesandu@test.com'
        )

    # All the tests
    def test_rbac_bouncer_logic(self):
        # This test verifies that the HasDynamicPermission class correctly checks the JWT for permissions.
        url = '/api/notifications/rules/'
        
        # Positive Test: User WITH permission
        mock_token = {'permissions': ['can_manage_notifications']}
        self.client.force_authenticate(user=self.user, token=mock_token)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Negative Test: Guest User(No permission attached)
        guest_user = User.objects.create_user(username='GuestUser', password='password123')
        self.client.force_authenticate(user=guest_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_username_bridge_sync(self):
        # This test checks that the username from auth_User table correctly maps to our UserData model.(user_user table)
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profile') 
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'Nesandu')

    def test_rule_validation_failure(self):
        # This test ensures that if we try to create a notification rule without required fields, we get a 400 Bad Request instead of a 500 Server Error.
        url = '/api/notifications/rules/'
        
        mock_token = {'permissions': ['can_manage_notifications']}
        self.client.force_authenticate(user=self.user, token=mock_token)
        
        # Bad Data: Missing recipients
        bad_data = {
            "name": "Invalid Rule",
            "event_trigger": "DOCUMENT_UPLOADED",
            "recipients": [] 
        }
        
        response = self.client.post(url, bad_data, format='json')
        self.assertEqual(response.status_code, 400)