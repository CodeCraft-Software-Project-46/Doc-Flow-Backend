# gets data from the AuditLog from DB and sends it to the frontend.
from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    # We grab the actual username instead of just sending the user ID number
    username = serializers.CharField(source='user.username', read_only=True, default='Anonymous')

    class Meta:
        model = AuditLog
        fields = [
            'id', 'username', 'action', 'document_id', 
            'previous_state', 'new_state', 'description', 'timestamp'
        ]