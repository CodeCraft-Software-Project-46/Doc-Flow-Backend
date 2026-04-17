# utils.py is providing utility functions for the audits app, such as logging actions to the AuditLog model.
# because logging is in many places, we can define log_action here so we don't repeat code.
from .models import AuditLog

def log_action(action, user=None, request=None, document_id=None, previous_state='', new_state='', description=''):
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            document_id=document_id,
            previous_state=previous_state,
            new_state=new_state,
            description=description,
        )
    except Exception as e:
        print(f"CRITICAL AUDIT LOG ERROR: {e}")