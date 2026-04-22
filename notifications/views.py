from rest_framework import generics, views, response, status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User

# Corrected Imports: Pull from your local models and the workflows app
from .models import NotificationRule, Notification
from .serializers import NotificationRuleSerializer, NotificationInboxSerializer
from .external_models import Role # Roles live in workflows, not accounts 
from accounts.permissions import HasDynamicPermission # Your custom security guard 

class NotificationRuleListView(generics.ListCreateAPIView):
    """
    GET: Sends all rules to the React Admin Dashboard.
    POST: Receives a new rule from the React popup form and saves it.
    """
    queryset = NotificationRule.objects.all().order_by('-created_at')
    serializer_class = NotificationRuleSerializer
    
    # Use your dynamic guard: only users with 'can_manage_notifications' enter [cite: 68, 1066]
    permission_classes = [HasDynamicPermission]
    required_permission = 'can_manage_notifications'

    def perform_create(self, serializer):
        # Automatically stamp the rule with the person who created it [cite: 364, 411]
        serializer.save(created_by=self.request.user)


class UserInboxView(generics.ListAPIView):
    """
    GET: Used by the React Sidebar Bell to see unread notifications.
    """
    serializer_class = NotificationInboxSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Privacy Filter: Only return notifications belonging to the logged-in user 
        return Notification.objects.filter(user=self.request.user)


class NotificationRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Handles GET (view detail), PATCH (toggle active/disable), and DELETE.
    """
    queryset = NotificationRule.objects.all()
    serializer_class = NotificationRuleSerializer
    permission_classes = [HasDynamicPermission]
    required_permission = 'can_manage_notifications'


class RecipientOptionsView(views.APIView):
    """
    Provides the list of Roles and Users for the React 'Add Rule' modal selection.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Pull dynamic roles from Avishka's workflow tables [cite: 769, 1146]
        roles = Role.objects.values_list('name', flat=True)
        # Pull all available users from the system [cite: 83, 105]
        users = User.objects.values_list('username', flat=True)
        
        return response.Response({
            "roles": [f"Role: {r}" for r in roles],
            "users": [f"User: {u}" for u in users]
        })