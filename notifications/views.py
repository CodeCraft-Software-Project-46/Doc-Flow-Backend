from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import NotificationRule, Notification
from .serializers import NotificationRuleSerializer, NotificationInboxSerializer

class NotificationRuleListView(generics.ListCreateAPIView):
    
    #GET: Sends all rules to the React Admin Dashboard.
    #POST: Receives a new rule from the React popup form and saves it.
    
    queryset = NotificationRule.objects.all().order_by('-created_at')
    serializer_class = NotificationRuleSerializer
    permission_classes = [IsAuthenticated] # can lock this down to specific roles later!

    def perform_create(self, serializer):
        # When saving, automatically stamp it with the user who clicked "Save"
        serializer.save(created_by=self.request.user) # to prevent users from creating rules pretending other users.


class UserInboxView(generics.ListAPIView):
    # GET: React hits this to see if the user has any unread notifications.

    serializer_class = NotificationInboxSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Security: Only return the notifications that belong to the person asking!
        return Notification.objects.filter(user=self.request.user)