# Checks if the user's roles contain the specific permission required by the view.
from rest_framework import permissions

class HasDynamicPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # 1. Reject if not logged in
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 2. What permission does this specific View require?
        required_perm = getattr(view, 'required_permission', None)
        
        # If the view doesn't declare a requirement, let them in safely
        if not required_perm:
            return True 
            
        # 3. Check Does this user have a role that contains this permission?
        has_perm = request.user.role_set.filter(permissions__name=required_perm).exists()
        
        return has_perm