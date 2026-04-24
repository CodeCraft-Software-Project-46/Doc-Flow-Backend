from rest_framework import generics, views, response, status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from audits.utils import log_action

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
        # 1. Capture the instance being saved
        instance = serializer.save(created_by=self.request.user)
        # 2. Log the creation action.
        log_action(
            action='NOTIFICATION_RULE_CREATED',
            user=self.request.user,
            request=self.request,
            description=f"New Notification Rule Created: {instance.name}" # Note: use 'name' as per your model
        )


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

    def perform_update(self, serializer):
        # 1. Get the current rule before the changes are saved
        old_instance = self.get_object()
        old_status = old_instance.is_active
        
        # 2. Save the new changes
        instance = serializer.save()
        
        # 3. Check: Did the user flip the 'active' switch, or just edit text?
        if old_status != instance.is_active:
            # It was a toggle (Enable/Disable)
            log_action(
                action='NOTIFICATION_RULE_TOGGLED',
                user=self.request.user,
                request=self.request,
                previous_state="Enabled" if old_status else "Disabled",
                new_state="Enabled" if instance.is_active else "Disabled",
                description=f"Notification Rule '{instance.name}' status changed."
            )
        else:
            # It was a regular edit (changed name, channel, etc.)
            log_action(
                action='NOTIFICATION_RULE_UPDATED',
                user=self.request.user,
                request=self.request,
                description=f"Notification Rule Edited: {instance.name}"
            )

    def perform_destroy(self, instance):
        # 4. Capture the name BEFORE the row is deleted from the DB
        rule_name = instance.name
        
        log_action(
            action='NOTIFICATION_RULE_DELETED',
            user=self.request.user,
            request=self.request,
            description=f"Notification Rule Deleted: {rule_name}"
        )
        
        # 5. Now actually delete the record
        instance.delete()


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