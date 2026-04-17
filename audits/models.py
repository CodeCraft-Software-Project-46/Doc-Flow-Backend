from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    # These are all the possible actions a user can take in DocFlow
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('LOGIN_FAILED', 'Failed Login Attempt'),
        ('DOCUMENT_VIEWED', 'Document Viewed'),
        ('DOCUMENT_ACCESS_DENIED', 'Unauthorized Document Access'),
        ('ACTION_TAKEN', 'Workflow Action Taken'),
        ('COMMENT_ADDED', 'Comment Added'),
        ('NOTIFICATION_VIEWED', 'Notifications Viewed'),
        ('NOTIFICATION_READ', 'Notification Marked Read'),
    ]
    # We allow null/blank for user because some actions (like failed login attempts) might not be associated with a valid user account
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    
    # We use basic fields here instead of strict ForeignKeys so if a document is deleted, 
    # the historical audit log of it survives!
    document_id = models.IntegerField(null=True, blank=True)
    previous_state = models.CharField(max_length=100, blank=True, default='')
    new_state = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp'] # Always show the newest logs first
        db_table = 'audit_logs'

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"[{self.timestamp}] {username} - {self.action}"