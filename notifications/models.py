from django.db import models
from django.contrib.auth.models import User

class NotificationRule(models.Model):

    # Stores dynamic notification triggers. Accessible by ANY user role that possesses the 'can_manage_notifications' permission.

    EVENT_CHOICES = [
        ('TASK_ASSIGNED', 'Task Assigned'),
        ('SLA_REMINDER', 'SLA Reminder'),
        ('SLA_BREACH', 'SLA Breach'),
        ('WORKFLOW_COMPLETED', 'Workflow Completed'),
        ('TASK_REJECTED', 'Task Rejected'),
        ('DOCUMENT_UPLOADED', 'Document Uploaded'),
        ('COMMENT_ADDED', 'Comment Added'),
        ('DOCUMENT_APPROVED', 'Document Approved'),
    ]

    CHANNEL_CHOICES = [
        ('EMAIL', 'Email Only'),
        ('IN_APP_ONLY', 'In-App Only'), 
        ('BOTH', 'Email + In-App'),
    ]

    name = models.CharField(max_length=100)
    event_trigger = models.CharField(max_length=50, choices=EVENT_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipients = models.JSONField(default=list) 
    is_active = models.BooleanField(default=True)
    
    # NEW: Tracks exactly which user (Admin, Manager, Intern) created this rule
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        creator = self.created_by.username if self.created_by else 'System'
        return f"{self.name} - {self.event_trigger} (By: {creator})"


class Notification(models.Model):
    """
    The user's personal Inbox.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()

    # This helps React decide which icon to show (Bell, Warning, Checkmark)
    event_type = models.CharField(
        max_length=50, 
        choices=NotificationRule.EVENT_CHOICES, 
        null=True, 
        blank=True
    )

    # Used to color-code the notification (Blue for Info, Red for Breach)
    LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Critical/Breach'),
    ]

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    related_record_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'notifications_inbox'

    def __str__(self):
        read_status = "READ" if self.is_read else "UNREAD"
        return f"[{read_status}] To {self.user.username}: {self.title}"