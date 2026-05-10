from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    Returns a list of all audit logs, newest first.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    
    # You must be authenticated to view audit logs
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        queryset = super().get_queryset() # Get the base queryset (all logs)
        action_filter = self.request.query_params.get('action') # Get the 'action' query parameter if it exists
        
        if action_filter:
            queryset = queryset.filter(action=action_filter)
            
        return queryset