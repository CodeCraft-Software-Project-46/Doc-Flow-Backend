from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    API Endpoint: GET /api/audits/logs/
    Returns a list of all audit logs, newest first.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    
    # You must be authenticated to view audit logs checks if token is valid and user is active.
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        # Allow the frontend to filter by action! Example: /api/audits/logs/?action=LOGIN_FAILED

        queryset = super().get_queryset() # Get the base queryset (all logs)
        action_filter = self.request.query_params.get('action') # Get the 'action' query parameter if it exists
        
        if action_filter:
            queryset = queryset.filter(action=action_filter)
            
        return queryset