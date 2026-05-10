from rest_framework import generics, views, response, status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from accounts.models import RoleData, UserData
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
    
    # Only users with 'can_manage_notifications' enter the Notification Dashboard, so only they can create/edit rules.
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
            description=f"New Notification Rule Created: {instance.name}"
        )

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import NotificationRule # Import your model
from accounts.models import RoleData # From our previous step

class NotificationMetadataView(APIView):
    """
    Returns all dynamic options for the Notification Rule modal.
    """
    def get(self, request):
        # 1. Get Event Choices from Model
        events = [
            {"value": key, "label": label} 
            for key, label in NotificationRule.EVENT_CHOICES
        ]

        # 2. Get Channel Choices from Model
        channels = [
            {"value": key, "label": label} 
            for key, label in NotificationRule.CHANNEL_CHOICES
        ]

        # 3. Get Roles from our Shadow Model (user_role table)
        roles = RoleData.objects.values_list('name', flat=True)

        return Response({
            "events": events,
            "channels": channels,
            "roles": list(roles)
        })

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
        # Pull dynamic roles from Avishka's workflow tables
        roles = RoleData.objects.values_list('name', flat=True)
        
        return response.Response({
            "roles": [f"{r}" for r in roles],
            "users": []
        })

class MarkNotificationReadView(views.APIView):
    """
    PATCH /api/notifications/inbox/<id>/read/
    Marks a single notification as read.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            # Security: Ensure the user can only mark THEIR OWN notifications as read
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.is_read = True
            notification.save()

            # Audit the reading action
            log_action(
                action='NOTIFICATION_READ',
                user=request.user,
                request=request,
                description=f"Marked notification '{notification.title}' as read"
            )

            return response.Response({"status": "success"})
        except Notification.DoesNotExist:
            return response.Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)