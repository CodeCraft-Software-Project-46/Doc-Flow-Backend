from rest_framework import serializers
from .models import NotificationRule, Notification

class NotificationRuleSerializer(serializers.ModelSerializer):
    # This serializer is for the notification rules. 
    
    # This automatically grabs the username of whoever created the rule
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = NotificationRule
        fields = [
            'id', 'name', 'event_trigger', 'channel', 
            'recipients', 'is_active', 'created_by_username', 'created_at'
        ]

class NotificationInboxSerializer(serializers.ModelSerializer):
    # This serializer is for showing the notifications in the user's inbox. It includes all the relevant info about each notification.
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'related_record_id', 
            'is_read', 'created_at'
        ]