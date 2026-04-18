from django.core.mail import send_mail
from .models import NotificationRule, Notification

def resolve_recipients(recipient_tags):
    # Takes a list of tags (e.g., ["Role: Manager", "User: admin"]) and returns a duplicate-free list of actual User objects.

    target_users = set() 

    if not recipient_tags:
        return []

    for tag in recipient_tags:
        # 1. DYNAMIC ROLE TARGETING (e.g., tag = "Role: Project Manager")
        if tag.startswith("Role:"):
            role_name = tag.split("Role:")[1].strip()
            
            # Find the role in the database and add all users attached to it
            matching_roles = Role.objects.filter(name=role_name)
            for role in matching_roles:
                target_users.update(role.users.all())
                
        # 2. SPECIFIC USER TARGETING (e.g., tag = "User: kasun_99")
        elif tag.startswith("User:"):
            username = tag.split("User:")[1].strip()
            
            # Find the exact user and add them
            try:
                user = User.objects.get(username=username)
                target_users.add(user)
            except User.DoesNotExist:
                # If the admin typed a name that doesn't exist, safely ignore it
                continue

    return list(target_users)


def dispatch_alert(event_trigger, title, message, related_record_id=None): # (what happened, what to say, which record to link to)
    # When an event happens (e.g., "Task Completed"), this function is called to send out notifications to the right people.

    # 1. THE FILTER: Find all active rules that care about this specific event
    active_rules = NotificationRule.objects.filter(
        event_trigger=event_trigger, 
        is_active=True
    )

    for rule in active_rules:
        # 2. THE SORTER: Get the exact list of humans to notify using your new tool
        target_users = resolve_recipients(rule.recipients)

        # 3. IN-APP DELIVERY: Drop it in their database inbox
        if rule.channel in ['IN_APP', 'BOTH']:
            # We use bulk_create to save all notifications in ONE database trip!
            # This is infinitely faster than saving them one-by-one in a loop.
            inbox_alerts = [
                Notification(
                    user=user,
                    title=title,
                    message=message,
                    related_record_id=related_record_id
                ) for user in target_users
            ]
            Notification.objects.bulk_create(inbox_alerts)


        # 4. EMAIL DELIVERY:
        if rule.channel in ['EMAIL', 'BOTH']:
            # Extract just the email addresses from our target users
            recipient_emails = [user.email for user in target_users if user.email]
            
            if recipient_emails:
                send_mail(
                    subject=f"DocFlow Alert: {title}",
                    message=message,
                    from_email=None, # This automatically uses DEFAULT_FROM_EMAIL
                    recipient_list=recipient_emails,
                    fail_silently=False, 
                )